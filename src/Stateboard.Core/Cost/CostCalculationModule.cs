using System.Text.Json;
using Stateboard.Core.Models;

namespace Stateboard.Core.Cost;

/// <summary>Loads local cloud pricebooks used by the calculation module.</summary>
public sealed class PriceBookStore
{
    private readonly Dictionary<string, JsonElement> _books = new(StringComparer.OrdinalIgnoreCase);

    public string AsOf { get; }

    public PriceBookStore(string? pricebooksDirectory = null)
    {
        AsOf = "2026-08-01";
        var dir = pricebooksDirectory
                  ?? Path.Combine(AppContext.BaseDirectory, "Pricebooks");
        foreach (var cloud in new[] { "aws", "azure", "gcp" })
        {
            var path = Path.Combine(dir, $"{cloud}.json");
            if (!File.Exists(path)) continue;
            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            _books[cloud] = doc.RootElement.Clone();
            if (doc.RootElement.TryGetProperty("asOf", out var asOf) && asOf.GetString() is { } s)
                AsOf = s;
        }
    }

    public UnitPrice? GetUnitPrice(string cloud, string family, string region, string sku)
    {
        if (!_books.TryGetValue(cloud, out var book)) return null;
        if (!TryFindProperty(book, family, out var fam)) return null;

        if (TryAmount(fam, region, sku, out var amount))
            return Make(family, amount);

        // Region fallback: same SKU from any known region in the book.
        foreach (var regProp in fam.EnumerateObject())
        {
            if (string.Equals(regProp.Name, region, StringComparison.OrdinalIgnoreCase))
                continue;
            if (TryAmount(fam, regProp.Name, sku, out amount))
                return Make(family, amount);
        }

        return null;
    }

    private static bool TryAmount(JsonElement fam, string region, string sku, out double amount)
    {
        amount = 0;
        if (!TryFindProperty(fam, region, out var reg))
            return false;

        if (TryFindProperty(reg, sku, out var amountEl) && amountEl.ValueKind == JsonValueKind.Number)
        {
            amount = amountEl.GetDouble();
            return true;
        }

        return false;
    }

    private static bool TryFindProperty(JsonElement obj, string name, out JsonElement value)
    {
        if (obj.TryGetProperty(name, out value))
            return true;
        foreach (var p in obj.EnumerateObject())
        {
            if (!string.Equals(p.Name, name, StringComparison.OrdinalIgnoreCase)) continue;
            value = p.Value;
            return true;
        }
        value = default;
        return false;
    }

    private UnitPrice Make(string family, double amount)
    {
        var unit = family is "compute" or "database" ? "hour"
            : family is "disk" or "object" ? "gb-month"
            : "month";
        return new UnitPrice
        {
            Amount = amount,
            Unit = unit,
            Source = "pricebook",
            AsOf = AsOf
        };
    }
}

public static class FamilyClassifier
{
    public static CostFamily Classify(string type)
    {
        var t = type.ToLowerInvariant();
        if (t.Contains("iam_") || t.Contains("_iam_") || t.Contains("_policy") || t.EndsWith("_role") ||
            t.Contains("security_group") ||
            t.Contains("network_security") || t.Contains("route_table") || t.Contains("subnet") ||
            t.Contains("virtual_network") || t.Contains("null_resource") || t.Contains("volume_attachment") ||
            t.Contains("cloudwatch_log") || t.Contains("firewall") || t.Contains("random_") || t.Contains("tls_") ||
            t.Contains("service_account") || t.Contains("secret_manager") || t.Contains("cloud_tasks") ||
            t.Contains("cloud_scheduler") || t.Contains("project_service") || t.Contains("terraform_data") ||
            t.Contains("artifact_registry") || t.Contains("project_iam") || t.Contains("pubsub_topic") ||
            t.Contains("storage_bucket_object") || t.Contains("bucket_object") ||
            t is "aws_vpc" or "google_compute_network" or "azurerm_virtual_network" ||
            (t.Contains("vpc") && !t.Contains("endpoint")))
            return CostFamily.Free;
        // Database before compute — aws_db_instance / sql_* contain "instance"/"sql".
        if (t.Contains("db_") || t.Contains("rds") || t.Contains("sql") || t.Contains("dynamodb") ||
            t.Contains("cosmos") || t.Contains("database_instance"))
            return CostFamily.Database;
        if (t.Contains("forwarding_rule") || t.Contains("load_balancer") || t.Contains("nat_gateway") ||
            t.Contains("natgateway") || t.Contains("public_ip") || t.Contains("application_gateway") ||
            t.Contains("_eip") || t.EndsWith("_lb") || t.Contains("_lb_"))
            return CostFamily.Network;
        if (t.Contains("virtual_machine") || t.Contains("compute_instance") || t.Contains("ecs_service") ||
            t.Contains("lambda") || t.Contains("kubernetes_cluster") || t.Contains("container_app") ||
            t.Contains("app_service") || t.Contains("cloud_run") || t.Contains("_instance") || t.EndsWith("_instance") ||
            t.Contains("aws_instance"))
            return CostFamily.Compute;
        if (t.Contains("ebs") || t.Contains("managed_disk") || t.Contains("compute_disk") ||
            (t.Contains("disk") && !t.Contains("attachment")) ||
            (t.Contains("volume") && !t.Contains("attachment")))
            return CostFamily.Disk;
        if (t.Contains("s3") || t.Contains("bucket") || t.Contains("storage_account") || t.Contains("storage_bucket"))
            return CostFamily.Object;
        if (t.Contains("lb") || t.Contains("gateway") || t.Contains("nat_"))
            return CostFamily.Network;
        return CostFamily.Other;
    }

    /// <summary>Free/meta resources that are still billed by usage when traffic exists.</summary>
    public static bool IsUsageBased(string type)
    {
        var t = type.ToLowerInvariant();
        return t.Contains("artifact_registry") || t.Contains("cloud_tasks") || t.Contains("cloud_scheduler") ||
               t.Contains("secret_manager") || t.Contains("pubsub") || t.Contains("ecr_");
    }
}

/// <summary>
/// Cost calculation module: classifies resources, looks up unit prices, aggregates $/mo.
/// </summary>
public sealed class CostCalculationModule
{
    private readonly PriceBookStore _prices;
    private const double DefaultHoursPerMonth = 730;

    public CostCalculationModule(PriceBookStore? prices = null)
    {
        _prices = prices ?? new PriceBookStore();
    }

    public CostReport Calculate(InfraGraph graph, double hoursPerMonth = DefaultHoursPerMonth)
    {
        var lines = new List<CostLine>();
        var warnings = new List<string>();
        var byCloud = new Dictionary<string, double>
        {
            ["aws"] = 0, ["azure"] = 0, ["gcp"] = 0, ["other"] = 0
        };
        var byFamily = Enum.GetValues<CostFamily>().ToDictionary(ToCamel, _ => 0.0);
        var uncovered = 0;
        var nodeType = graph.Nodes.ToDictionary(n => n.Id, n => n.Type, StringComparer.Ordinal);

        foreach (var node in graph.Nodes)
        {
            var family = FamilyClassifier.Classify(node.Type);
            var familyKey = ToCamel(family);

            if (family == CostFamily.Free)
            {
                var freeBasis = FamilyClassifier.IsUsageBased(node.Type)
                    ? "usage-based (not modeled)"
                    : "free / meta resource";
                lines.Add(Line(node, familyKey, 0, "high", freeBasis));
                continue;
            }

            if (node.Cloud is "other" || family == CostFamily.Other)
            {
                uncovered++;
                lines.Add(Line(node, familyKey, 0, "unknown", "no pricing rule"));
                continue;
            }

            var region = node.Attrs.Region ?? DefaultRegion(node.Cloud);
            var sku = ResolveSku(node, family);
            if (string.IsNullOrEmpty(sku))
            {
                uncovered++;
                lines.Add(Line(node, familyKey, 0, "low", "missing sku"));
                continue;
            }

            var price = _prices.GetUnitPrice(node.Cloud, familyKey, region, sku);
            if (price is null)
            {
                uncovered++;
                lines.Add(Line(node, familyKey, 0, "unknown", $"no price for {sku} @ {region}"));
                continue;
            }

            var (monthly, basis) = ToMonthly(node, price, sku, hoursPerMonth);
            byCloud[node.Cloud] = byCloud.GetValueOrDefault(node.Cloud) + monthly;
            byFamily[familyKey] = byFamily.GetValueOrDefault(familyKey) + monthly;
            lines.Add(Line(node, familyKey, monthly, "medium", basis, price));
        }

        if (_prices.AsOf is { Length: > 0 } && lines.Count > 0)
            warnings.Add($"Prices from local pricebooks as of {_prices.AsOf}");

        return new CostReport
        {
            AsOf = _prices.AsOf,
            HoursPerMonth = hoursPerMonth,
            TotalMonthlyUsd = Math.Round(lines.Sum(l => l.MonthlyUsd), 4),
            ByCloud = byCloud.ToDictionary(kv => kv.Key, kv => Math.Round(kv.Value, 4)),
            ByModule = graph.Modules.Select(m => new ModuleCost
            {
                Path = m.Path,
                NodeCount = m.NodeIds.Count,
                MonthlyUsd = Math.Round(lines.Where(l => m.NodeIds.Contains(l.NodeId)).Sum(l => l.MonthlyUsd), 4)
            }).ToList(),
            ByType = lines
                .GroupBy(l => nodeType.GetValueOrDefault(l.NodeId, "unknown"))
                .Select(g => new TypeCost
                {
                    Type = g.Key,
                    NodeCount = g.Count(),
                    MonthlyUsd = Math.Round(g.Sum(x => x.MonthlyUsd), 4)
                })
                .OrderByDescending(t => t.MonthlyUsd)
                .ToList(),
            ByFamily = byFamily.ToDictionary(kv => kv.Key, kv => Math.Round(kv.Value, 4)),
            Lines = lines,
            UncoveredCount = uncovered,
            Warnings = warnings
        };
    }

    private static string? ResolveSku(InfraNode node, CostFamily family)
    {
        if (!string.IsNullOrEmpty(node.Attrs.Sku))
            return node.Attrs.Sku;

        return (node.Cloud, family) switch
        {
            ("aws", CostFamily.Disk) => "gp3",
            ("aws", CostFamily.Object) => "standard",
            ("aws", CostFamily.Network) => "alb",
            ("aws", CostFamily.Compute) => "t3.micro",
            ("aws", CostFamily.Database) => "db.t3.micro",
            ("azure", CostFamily.Disk) => "Premium_LRS",
            ("azure", CostFamily.Object) => "hot",
            ("azure", CostFamily.Network) => "load_balancer",
            ("azure", CostFamily.Compute) => "Standard_B1s",
            ("azure", CostFamily.Database) => "Basic",
            ("gcp", CostFamily.Disk) => "pd-ssd",
            ("gcp", CostFamily.Object) => "standard",
            ("gcp", CostFamily.Network) => "forwarding_rule",
            ("gcp", CostFamily.Compute) => "e2-micro",
            ("gcp", CostFamily.Database) => "db-f1-micro",
            _ => null
        };
    }

    private static (double Monthly, string Basis) ToMonthly(
        InfraNode node, UnitPrice price, string sku, double hours)
    {
        if (price.Unit == "hour")
            return (price.Amount * hours, $"{sku} × {hours}h");
        if (price.Unit == "gb-month")
        {
            var gb = node.Attrs.StorageGb ?? 1;
            return (price.Amount * gb, $"{gb} GB × ${price.Amount}/GB-mo");
        }
        return (price.Amount, $"{sku} monthly");
    }

    private static string DefaultRegion(string cloud) => cloud switch
    {
        "aws" => "us-east-1",
        "azure" => "westeurope",
        "gcp" => "us-central1",
        _ => "global"
    };

    private static CostLine Line(
        InfraNode node, string family, double monthly, string confidence, string basis, UnitPrice? price = null) =>
        new()
        {
            NodeId = node.Id,
            Address = node.Address,
            Cloud = node.Cloud,
            Family = family,
            MonthlyUsd = monthly,
            Confidence = confidence,
            Basis = basis,
            UnitPrice = price
        };

    private static string ToCamel(CostFamily f) =>
        char.ToLowerInvariant(f.ToString()[0]) + f.ToString()[1..];
}
