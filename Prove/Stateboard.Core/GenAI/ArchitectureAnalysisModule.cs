using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Stateboard.Core.Models;

namespace Stateboard.Core.GenAI;

/// <summary>
/// Separate GenAI module: uses Gemini to explain architecture purpose and
/// what workloads / capabilities the estate is set up to support.
/// </summary>
public sealed class ArchitectureAnalysisModule
{
    private readonly GeminiOptions _options;
    private readonly HttpClient _http;
    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };

    public ArchitectureAnalysisModule(GeminiOptions options, HttpClient? http = null)
    {
        _options = options;
        _http = http ?? new HttpClient { Timeout = TimeSpan.FromSeconds(60) };
    }

    public bool IsConfigured => !string.IsNullOrWhiteSpace(_options.ApiKey);

    public async Task<ArchitectureAnalysis> AnalyzeAsync(
        InfraGraph graph,
        CostReport costs,
        CancellationToken ct = default)
    {
        if (!IsConfigured)
        {
            var local = HeuristicAnalyze(graph, costs);
            local.Source = "local";
            local.Configured = false;
            local.Model = "heuristic";
            local.Summary = string.IsNullOrEmpty(local.Summary)
                ? local.Summary
                : local.Summary + " Set GEMINI_API_KEY (or Gemini:ApiKey) for Gemini analysis.";
            return local;
        }

        try
        {
            var prompt = BuildPrompt(graph, costs);
            var raw = await CallGeminiAsync(prompt, ct);
            var parsed = ParseResponse(raw) ?? HeuristicAnalyze(graph, costs);
            parsed.Model = _options.Model;
            parsed.Source = "gemini";
            parsed.Configured = true;
            return parsed;
        }
        catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException or JsonException or InvalidOperationException)
        {
            var fallback = HeuristicAnalyze(graph, costs);
            fallback.Source = "local-fallback";
            fallback.Configured = true;
            fallback.Model = _options.Model;
            fallback.Summary = $"{fallback.Summary} (Gemini unavailable — using local heuristic.)";
            return fallback;
        }
    }

    private async Task<string> CallGeminiAsync(string prompt, CancellationToken ct)
    {
        var url =
            $"{_options.ApiBase.TrimEnd('/')}/models/{_options.Model}:generateContent";

        var body = new
        {
            contents = new[]
            {
                new { parts = new[] { new { text = prompt } } }
            },
            generationConfig = new
            {
                temperature = 0.35,
                responseMimeType = "application/json"
            }
        };

        using var req = new HttpRequestMessage(HttpMethod.Post, url);
        req.Headers.TryAddWithoutValidation("x-goog-api-key", _options.ApiKey);
        req.Content = JsonContent.Create(body);

        using var res = await _http.SendAsync(req, ct);
        var payload = await res.Content.ReadAsStringAsync(ct);
        if (!res.IsSuccessStatusCode)
            throw new InvalidOperationException($"Gemini HTTP {(int)res.StatusCode}: {Trim(payload, 240)}");

        using var doc = JsonDocument.Parse(payload);
        var text = doc.RootElement
            .GetProperty("candidates")[0]
            .GetProperty("content")
            .GetProperty("parts")[0]
            .GetProperty("text")
            .GetString();

        if (string.IsNullOrWhiteSpace(text))
            throw new InvalidOperationException("Gemini returned empty content.");
        return text;
    }

    private static ArchitectureAnalysis? ParseResponse(string raw)
    {
        var json = ExtractJsonObject(raw);
        if (json is null) return null;
        var dto = JsonSerializer.Deserialize<GeminiAnalysisDto>(json, JsonOpts);
        if (dto is null || string.IsNullOrWhiteSpace(dto.Purpose)) return null;
        return new ArchitectureAnalysis
        {
            Purpose = dto.Purpose.Trim(),
            Supports = (dto.Supports ?? dto.Holds ?? "").Trim(),
            Capabilities = dto.Capabilities ?? [],
            Workloads = dto.Workloads ?? [],
            Risks = dto.Risks ?? [],
            Improvements = dto.Improvements ?? [],
            ModuleSplits = dto.ModuleSplits ?? dto.Modules ?? [],
            Summary = (dto.Summary ?? "").Trim()
        };
    }

    private static string? ExtractJsonObject(string raw)
    {
        var t = raw.Trim();
        if (t.StartsWith("```", StringComparison.Ordinal))
        {
            var start = t.IndexOf('{');
            var end = t.LastIndexOf('}');
            if (start >= 0 && end > start) return t[start..(end + 1)];
        }
        var i = t.IndexOf('{');
        var j = t.LastIndexOf('}');
        if (i >= 0 && j > i) return t[i..(j + 1)];
        return null;
    }

    internal static string BuildPrompt(InfraGraph graph, CostReport costs)
    {
        var sb = new StringBuilder();
        sb.AppendLine("You are a cloud architect reviewing a Terraform estate scanned by Stateboard.");
        sb.AppendLine("Explain the purpose of this architecture and what it is designed to support/hold.");
        sb.AppendLine("Then recommend concrete improvements and how to split the estate into Terraform modules.");
        sb.AppendLine("Be concrete and business-oriented. Do not invent resources that are not listed.");
        sb.AppendLine();
        sb.AppendLine("Return ONLY JSON with this shape:");
        sb.AppendLine("""
            {
              "purpose": "1-2 sentences: overall purpose of this architecture",
              "supports": "1-3 sentences: what systems/workloads/data it is set up to support or hold",
              "capabilities": ["short capability bullets"],
              "workloads": ["likely workload types this estate can run"],
              "risks": ["notable gaps or risks visible from the resources"],
              "improvements": ["actionable improvements: cost, reliability, security, operability"],
              "moduleSplits": ["suggested Terraform module boundaries, e.g. modules/network — VPC, subnets, SGs"],
              "summary": "one short paragraph overview"
            }
            """);
        sb.AppendLine();
        sb.AppendLine($"Source: {graph.Meta.Source ?? "unknown"}");
        sb.AppendLine($"Resources: {graph.Nodes.Count}");
        sb.AppendLine($"Estimated monthly cost (USD): {costs.TotalMonthlyUsd:F2}");
        sb.AppendLine($"By family: {string.Join(", ", costs.ByFamily.Where(kv => kv.Value > 0).Select(kv => $"{kv.Key}=${kv.Value:F0}"))}");
        sb.AppendLine($"Clouds: {string.Join(", ", costs.ByCloud.Where(kv => kv.Value > 0 || graph.Nodes.Any(n => n.Cloud == kv.Key)).Select(kv => kv.Key))}");
        sb.AppendLine();
        sb.AppendLine("Current modules (from paths):");
        foreach (var m in graph.Modules.Take(20))
            sb.AppendLine($"- {m.Path} ({m.NodeIds.Count} resources)");
        if (graph.Modules.Count == 0)
            sb.AppendLine("- (none detected — most resources may live in root)");
        sb.AppendLine();
        sb.AppendLine("Resources (type · name · group · module · sku · $/mo):");
        var costById = costs.Lines.ToDictionary(l => l.NodeId, l => l, StringComparer.Ordinal);
        foreach (var n in graph.Nodes.Take(80))
        {
            costById.TryGetValue(n.Id, out var line);
            var mod = string.IsNullOrEmpty(n.ModulePath) ? "root" : n.ModulePath;
            sb.AppendLine(
                $"- {n.Type} · {n.Name} · {n.SpriteKind} · {mod} · sku={n.Attrs.Sku ?? "-"} · ${(line?.MonthlyUsd ?? 0):F2}");
        }
        if (graph.Nodes.Count > 80)
            sb.AppendLine($"… and {graph.Nodes.Count - 80} more");
        return sb.ToString();
    }

    public static ArchitectureAnalysis HeuristicAnalyze(InfraGraph graph, CostReport costs)
    {
        var types = graph.Nodes.Select(n => n.Type.ToLowerInvariant()).ToList();
        var groups = graph.Nodes
            .GroupBy(n => n.SpriteKind)
            .ToDictionary(g => g.Key, g => g.Count(), StringComparer.OrdinalIgnoreCase);

        var hasWeb = types.Any(t => t.Contains("lb") || t.Contains("instance") || t.Contains("app_service") || t.Contains("cloud_run"));
        var hasDb = types.Any(t => t.Contains("db") || t.Contains("sql") || t.Contains("rds") || t.Contains("dynamodb"));
        var hasStorage = types.Any(t => t.Contains("s3") || t.Contains("bucket") || t.Contains("storage") || t.Contains("ebs") || t.Contains("disk"));
        var hasNet = types.Any(t => t.Contains("vpc") || t.Contains("subnet") || t.Contains("network"));

        var purposeParts = new List<string>();
        if (hasWeb && hasDb) purposeParts.Add("a typical application stack with compute in front of managed data");
        else if (hasWeb) purposeParts.Add("compute / edge delivery for application traffic");
        else if (hasDb) purposeParts.Add("data persistence and database services");
        else purposeParts.Add("cloud infrastructure defined in Terraform");

        if (hasNet) purposeParts.Add("with dedicated network fabric");

        var purpose = $"This estate looks like {string.Join(", ", purposeParts)}.";

        var supports = new StringBuilder("It appears set up to hold ");
        var hold = new List<string>();
        if (hasWeb) hold.Add("application or API traffic");
        if (hasDb) hold.Add("structured application data");
        if (hasStorage) hold.Add("files, disks, or object assets");
        if (hold.Count == 0) hold.Add("the scanned Terraform resources as declared");
        supports.Append(string.Join(", ", hold));
        supports.Append('.');

        var capabilities = new List<string>();
        if (groups.GetValueOrDefault("compute") > 0) capabilities.Add("Run compute workloads (VMs / services)");
        if (groups.GetValueOrDefault("database") > 0) capabilities.Add("Persist relational or managed data");
        if (groups.GetValueOrDefault("storage") > 0) capabilities.Add("Store disks/objects for apps and backups");
        if (groups.GetValueOrDefault("network") > 0) capabilities.Add("Route and isolate traffic across the estate");
        if (capabilities.Count == 0) capabilities.Add("Provision the listed Terraform resources");

        var workloads = new List<string>();
        if (hasWeb && hasDb) workloads.Add("Web / API application");
        if (hasWeb) workloads.Add("Stateless or lightly stateful services");
        if (hasDb) workloads.Add("Transactional data store");
        if (hasStorage) workloads.Add("Asset or backup storage");
        if (workloads.Count == 0) workloads.Add("General cloud infrastructure");

        var risks = new List<string>();
        if (costs.UncoveredCount > 0)
            risks.Add($"{costs.UncoveredCount} resources lack pricing coverage");
        if (!hasDb && hasWeb)
            risks.Add("Compute/load balancing present without a clear database in scan");
        if (!hasNet)
            risks.Add("Little explicit network fabric in the scan — may live elsewhere");

        var rootHeavy = graph.Nodes.Count(n => string.IsNullOrEmpty(n.ModulePath));
        var improvements = new List<string>();
        if (rootHeavy >= Math.Max(4, graph.Nodes.Count / 2))
            improvements.Add("Move root-level resources into domain modules (network, compute, data, storage)");
        if (hasWeb && hasDb)
            improvements.Add("Separate app/compute from data stores so DB changes do not force app redeploys");
        if (hasNet)
            improvements.Add("Keep network + security groups in their own module with stable outputs for dependents");
        if (costs.UncoveredCount > 0)
            improvements.Add("Add missing SKU/region attributes so cost estimates cover more of the estate");
        if (improvements.Count == 0)
            improvements.Add("Add clear module boundaries and outputs between network, compute, and data");

        var moduleSplits = new List<string>();
        foreach (var (kind, label, reason) in new (string, string, string)[]
                 {
                     ("network", "modules/network", "VPC, subnets, gateways, security groups"),
                     ("compute", "modules/compute", "instances, services, load balancers"),
                     ("database", "modules/data", "RDS/SQL and related data services"),
                     ("storage", "modules/storage", "buckets, disks, and object stores"),
                 })
        {
            if (groups.GetValueOrDefault(kind) > 0)
                moduleSplits.Add($"{label} — {reason}");
        }
        if (moduleSplits.Count == 0)
            moduleSplits.Add("modules/core — group related resources by lifecycle and ownership");

        return new ArchitectureAnalysis
        {
            Purpose = purpose,
            Supports = supports.ToString(),
            Capabilities = capabilities,
            Workloads = workloads,
            Risks = risks,
            Improvements = improvements,
            ModuleSplits = moduleSplits,
            Summary =
                $"{graph.Nodes.Count} resources · ~${costs.TotalMonthlyUsd:F0}/mo estimated. " +
                $"{purpose} {supports}"
        };
    }

    private static string Trim(string s, int max) =>
        s.Length <= max ? s : s[..max] + "…";

    private sealed class GeminiAnalysisDto
    {
        public string? Purpose { get; set; }
        public string? Supports { get; set; }
        public string? Holds { get; set; }
        public List<string>? Capabilities { get; set; }
        public List<string>? Workloads { get; set; }
        public List<string>? Risks { get; set; }
        public List<string>? Improvements { get; set; }
        public List<string>? ModuleSplits { get; set; }
        public List<string>? Modules { get; set; }
        public string? Summary { get; set; }
    }
}
