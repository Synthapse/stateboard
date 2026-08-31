using System.Text.RegularExpressions;
using Stateboard.Core.Models;

namespace Stateboard.Core.Scanning;

/// <summary>
/// Lightweight HCL scanner: finds resource/module blocks and cross-references.
/// Not a full HCL parser — good enough for architecture visualization.
/// </summary>
public sealed partial class TerraformHclScanner
{
    private static readonly Regex ResourceBlock = ResourceBlockRegex();
    private static readonly Regex ModuleBlock = ModuleBlockRegex();
    private static readonly Regex AttrString = AttrStringRegex();
    private static readonly Regex AttrNumber = AttrNumberRegex();
    private static readonly Regex ResourceRef = ResourceRefRegex();
    private static readonly Regex ModuleRef = ModuleRefRegex();

    public InfraGraph ScanDirectory(string rootPath, string? sourceLabel = null)
    {
        if (!Directory.Exists(rootPath))
            throw new DirectoryNotFoundException($"Terraform path not found: {rootPath}");

        var tfFiles = Directory
            .EnumerateFiles(rootPath, "*.tf", SearchOption.AllDirectories)
            .Where(p => !p.Contains($"{Path.DirectorySeparatorChar}.terraform{Path.DirectorySeparatorChar}"))
            .OrderBy(p => p, StringComparer.Ordinal)
            .ToList();

        if (tfFiles.Count == 0)
            throw new InvalidOperationException($"No .tf files under {rootPath}");

        var nodes = new List<InfraNode>();
        var modulePaths = new HashSet<string>(StringComparer.Ordinal) { "" };

        foreach (var file in tfFiles)
        {
            var relative = Path.GetRelativePath(rootPath, file).Replace('\\', '/');
            var modulePath = InferModulePath(relative);
            modulePaths.Add(modulePath);

            var text = File.ReadAllText(file);
            foreach (Match m in ResourceBlock.Matches(text))
            {
                var type = m.Groups["type"].Value;
                var name = m.Groups["name"].Value;
                var body = m.Groups["body"].Value;
                var address = string.IsNullOrEmpty(modulePath)
                    ? $"{type}.{name}"
                    : $"module.{modulePath.Replace('/', '.')}.{type}.{name}";

                var cloud = CloudDetection.FromType(type);
                var attrs = ExtractAttrs(type, body);
                var deps = ExtractDependencies(body, modulePath);

                nodes.Add(new InfraNode
                {
                    Id = address,
                    Address = address,
                    Type = type,
                    Name = name,
                    Cloud = cloud.ToString().ToLowerInvariant(),
                    Provider = cloud switch
                    {
                        Cloud.Aws => "aws",
                        Cloud.Azure => "azurerm",
                        Cloud.Gcp => "google",
                        _ => "unknown"
                    },
                    ModulePath = modulePath,
                    Dependencies = deps,
                    Attrs = attrs,
                    SpriteKind = SpriteMapping.FromType(type).ToString().ToLowerInvariant()
                });
            }

            // Local module declarations become module folders already scanned via nested .tf;
            // keep declaration names for dependency edges only.
            foreach (Match m in ModuleBlock.Matches(text))
            {
                _ = m; // modules are represented by nested paths + module.* refs
            }
        }

        var modules = modulePaths
            .OrderBy(p => p, StringComparer.Ordinal)
            .Select(p => new InfraModule
            {
                Path = p,
                NodeIds = nodes.Where(n => n.ModulePath == p).Select(n => n.Id).ToList()
            })
            .Where(m => m.NodeIds.Count > 0 || m.Path == "")
            .ToList();

        return new InfraGraph
        {
            Meta = new InfraMeta
            {
                TerraformVersion = "hcl-scan",
                Serial = nodes.Count,
                Lineage = Guid.NewGuid().ToString("N")[..12],
                Source = sourceLabel ?? rootPath
            },
            Nodes = nodes,
            Modules = modules
        };
    }

    private static string InferModulePath(string relativeTfFile)
    {
        // modules/network/main.tf → network
        // modules/network/vpc/main.tf → network/vpc
        var dir = Path.GetDirectoryName(relativeTfFile)?.Replace('\\', '/') ?? "";
        if (dir.StartsWith("modules/", StringComparison.Ordinal))
            return dir["modules/".Length..];
        if (dir is "" or ".")
            return "";
        // nested non-modules folder still groups by directory
        return dir;
    }

    private static CostAttrs ExtractAttrs(string type, string body)
    {
        var attrs = new CostAttrs();

        if (MatchNamedString(body, "region") is { } region)
            attrs.Region = region;
        else if (MatchNamedString(body, "location") is { } location)
            attrs.Region = location;
        else if (MatchNamedString(body, "availability_zone") is { } zone && zone.Length > 1)
            attrs.Region = zone[..^1]; // us-east-1a → us-east-1
        else if (MatchNamedString(body, "zone") is { } gZone)
            attrs.Region = gZone.Contains('-') && gZone.Length > 2 ? gZone[..^2] : gZone; // us-central1-a → us-central1

        // Azure VM uses size/vm_size strings; disk size is numeric — prefer string SKUs first.
        attrs.Sku =
            MatchNamedString(body, "instance_type")
            ?? MatchNamedString(body, "instance_class")
            ?? MatchNamedString(body, "sku_name")
            ?? MatchNamedString(body, "machine_type")
            ?? MatchNamedString(body, "vm_size")
            ?? MatchNamedString(body, "storage_account_type")
            ?? MatchNamedString(body, "tier")
            ?? MatchNamedString(body, "size")
            ?? MatchNamedString(body, "type");

        if (type.Contains("nat_gateway", StringComparison.OrdinalIgnoreCase) ||
            type.Contains("natgateway", StringComparison.OrdinalIgnoreCase))
            attrs.Sku ??= "nat_gateway";
        if (type is "aws_lb" or "aws_alb" || MatchNamedString(body, "load_balancer_type") == "application")
            attrs.Sku ??= "alb";
        if (type.Contains("lb", StringComparison.OrdinalIgnoreCase) && type.StartsWith("azurerm", StringComparison.Ordinal))
            attrs.Sku ??= "load_balancer";
        if (type.Contains("forwarding_rule", StringComparison.OrdinalIgnoreCase))
            attrs.Sku ??= "forwarding_rule";

        if (MatchNamedNumber(body, "disk_size_gb") is { } diskGb)
            attrs.StorageGb = diskGb;
        else if (MatchNamedNumber(body, "allocated_storage") is { } alloc)
            attrs.StorageGb = alloc;
        else if (MatchNamedString(body, "size") is null && MatchNamedNumber(body, "size") is { } size)
            attrs.StorageGb = size; // numeric size = GB; string size = Azure VM SKU
        else if (MatchNamedNumber(body, "size") is { } sizeNum &&
                 (type.Contains("disk", StringComparison.OrdinalIgnoreCase) ||
                  type.Contains("volume", StringComparison.OrdinalIgnoreCase) ||
                  type.Contains("ebs", StringComparison.OrdinalIgnoreCase)))
            attrs.StorageGb = sizeNum;

        return attrs;
    }

    private static string? MatchNamedString(string body, string name)
    {
        foreach (Match m in AttrString.Matches(body))
        {
            if (m.Groups["name"].Value == name)
                return m.Groups["value"].Value;
        }
        return null;
    }

    private static double? MatchNamedNumber(string body, string name)
    {
        foreach (Match m in AttrNumber.Matches(body))
        {
            if (m.Groups["name"].Value == name && double.TryParse(m.Groups["value"].Value, out var v))
                return v;
        }
        return null;
    }

    private static List<string> ExtractDependencies(string body, string modulePath)
    {
        // Drop quoted strings so SKUs like "db.t3.micro" are not treated as refs.
        var scrubbed = Regex.Replace(body, @"""[^""]*""", "\"\"");
        var deps = new HashSet<string>(StringComparer.Ordinal);
        foreach (Match m in ResourceRef.Matches(scrubbed))
        {
            var type = m.Groups["type"].Value;
            var name = m.Groups["name"].Value;
            if (type is "var" or "local" or "data" or "path" or "terraform" or "each" or "count" or "self")
                continue;
            var address = string.IsNullOrEmpty(modulePath)
                ? $"{type}.{name}"
                : $"module.{modulePath.Replace('/', '.')}.{type}.{name}";
            deps.Add(address);
        }

        foreach (Match m in ModuleRef.Matches(scrubbed))
        {
            var mod = m.Groups["mod"].Value;
            deps.Add($"module.{mod}");
        }

        return deps.ToList();
    }

    [GeneratedRegex(
        @"resource\s+""(?<type>[^""]+)""\s+""(?<name>[^""]+)""\s*\{(?<body>(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}",
        RegexOptions.Singleline | RegexOptions.Compiled)]
    private static partial Regex ResourceBlockRegex();

    [GeneratedRegex(
        @"module\s+""(?<name>[^""]+)""\s*\{(?<body>(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}",
        RegexOptions.Singleline | RegexOptions.Compiled)]
    private static partial Regex ModuleBlockRegex();

    [GeneratedRegex(@"(?<name>[a-zA-Z0-9_]+)\s*=\s*""(?<value>[^""]*)""", RegexOptions.Compiled)]
    private static partial Regex AttrStringRegex();

    [GeneratedRegex(@"(?<name>[a-zA-Z0-9_]+)\s*=\s*(?<value>\d+(?:\.\d+)?)", RegexOptions.Compiled)]
    private static partial Regex AttrNumberRegex();

    [GeneratedRegex(@"\b(?<type>[a-zA-Z0-9_]+)\.(?<name>[a-zA-Z0-9_]+)\.[a-zA-Z0-9_]+", RegexOptions.Compiled)]
    private static partial Regex ResourceRefRegex();

    [GeneratedRegex(@"\bmodule\.(?<mod>[a-zA-Z0-9_]+)\.", RegexOptions.Compiled)]
    private static partial Regex ModuleRefRegex();
}

public static class CloudDetection
{
    public static Cloud FromType(string type)
    {
        if (type.StartsWith("aws_", StringComparison.OrdinalIgnoreCase)) return Cloud.Aws;
        if (type.StartsWith("azurerm_", StringComparison.OrdinalIgnoreCase) ||
            type.StartsWith("azuread_", StringComparison.OrdinalIgnoreCase)) return Cloud.Azure;
        if (type.StartsWith("google_", StringComparison.OrdinalIgnoreCase)) return Cloud.Gcp;
        return Cloud.Other;
    }
}

public static class SpriteMapping
{
    public static SpriteKind FromType(string type)
    {
        var t = type.ToLowerInvariant();

        // Cloud Run services/jobs are compute; only their IAM bindings stay identity.
        var isCloudRun = t.Contains("cloud_run") || t.Contains("cloudrun");
        var isIam = t.Contains("iam_") || t.Contains("_iam_") || t.EndsWith("_iam");
        if (isCloudRun && isIam)
            return SpriteKind.Identity;
        if (isCloudRun)
            return SpriteKind.Compute;

        // IAM / secrets — including storage/bucket IAM bindings (not the buckets themselves).
        if (t.Contains("service_account") || t.Contains("secret_manager") || isIam ||
            t.Contains("_role") || t.Contains("random_password") || t.Contains("kms_") ||
            (t.Contains("policy") && !t.Contains("bucket") && !t.Contains("storage")))
            return SpriteKind.Identity;

        if (t.Contains("artifact_registry") || t.Contains("container_registry") || t.Contains("ecr_") ||
            t.Contains("s3") || t.Contains("bucket") || t.Contains("ebs") ||
            (t.Contains("disk") && !t.Contains("attachment")) ||
            t.Contains("storage") || (t.Contains("volume") && !t.Contains("attachment")))
            return SpriteKind.Storage;

        if (t.Contains("db") || t.Contains("rds") || t.Contains("sql") || t.Contains("dynamodb") || t.Contains("cosmos"))
            return SpriteKind.Database;

        if (t.Contains("vpc") || t.Contains("subnet") || t.Contains("forwarding_rule") || t.Contains("firewall") ||
            t.Contains("security_group") || t.Contains("route") || t.Contains("gateway") ||
            t.Contains("_lb") || t.EndsWith("_lb") || t.Contains("load_balancer") ||
            t.Contains("network"))
            return SpriteKind.Network;

        if (t.Contains("cloud_tasks") || t.Contains("cloud_scheduler") || t.Contains("cloud_functions") ||
            t.Contains("pubsub") || t.Contains("sqs") || t.Contains("lambda") ||
            t.Contains("ecs") || t.Contains("instance") || t.Contains("vm") || t.Contains("compute") ||
            t.Contains("app_service") || t.Contains("container_app") || t.Contains("container_cluster"))
            return SpriteKind.Compute;

        return SpriteKind.Generic;
    }
}
