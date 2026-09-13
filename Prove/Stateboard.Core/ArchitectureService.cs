using Stateboard.Core.Cost;
using Stateboard.Core.Models;
using Stateboard.Core.Scanning;
using Stateboard.Core.Visualization;

namespace Stateboard.Core;

public sealed class ScanRequest
{
    /// <summary>Git HTTPS URL of an external Terraform repo.</summary>
    public string? GitUrl { get; set; }

    /// <summary>Optional branch / tag for clone.</summary>
    public string? Ref { get; set; }

    /// <summary>Absolute or relative local path (dev / CI).</summary>
    public string? LocalPath { get; set; }

    /// <summary>Built-in fixture name, e.g. "sample".</summary>
    public string? Fixture { get; set; }

    /// <summary>Subdirectory inside the repo that contains Terraform root.</summary>
    public string? TerraformRoot { get; set; }
}

/// <summary>
/// Orchestrates: fetch external repo → scan HCL → calculate costs → build hex visualization.
/// </summary>
public sealed class ArchitectureService
{
    private readonly TerraformHclScanner _scanner;
    private readonly GitRepoFetcher _git;
    private readonly CostCalculationModule _costs;
    private readonly HexLayoutEngine _layout;
    private readonly string _fixturesRoot;
    private readonly string[] _allowedLocalRoots;

    public ArchitectureService(
        string fixturesRoot,
        IEnumerable<string>? allowedLocalRoots = null,
        CostCalculationModule? costs = null)
    {
        _fixturesRoot = fixturesRoot;
        _allowedLocalRoots = (allowedLocalRoots ?? []).Select(Path.GetFullPath).ToArray();
        _scanner = new TerraformHclScanner();
        _git = new GitRepoFetcher();
        _costs = costs ?? new CostCalculationModule();
        _layout = new HexLayoutEngine();
    }

    public async Task<ArchitectureScanResult> ScanAsync(ScanRequest request, CancellationToken ct = default)
    {
        string rootDir;
        string label;
        var cleanup = false;

        if (!string.IsNullOrWhiteSpace(request.Fixture))
        {
            rootDir = Path.GetFullPath(Path.Combine(
                _fixturesRoot,
                request.Fixture == "sample" ? "sample-terraform" : request.Fixture));
            label = $"fixture:{request.Fixture}";
        }
        else if (!string.IsNullOrWhiteSpace(request.GitUrl))
        {
            rootDir = await _git.CloneAsync(request.GitUrl!, request.Ref, ct);
            label = GitRepoFetcher.NormalizeUrl(request.GitUrl!);
            cleanup = true;
        }
        else if (!string.IsNullOrWhiteSpace(request.LocalPath))
        {
            rootDir = Path.GetFullPath(request.LocalPath!);
            EnsureAllowedLocal(rootDir);
            label = rootDir;
        }
        else
        {
            throw new ArgumentException("Provide fixture, gitUrl, or localPath.");
        }

        try
        {
            var workDir = TerraformRootFinder.Resolve(rootDir, request.TerraformRoot);
            var relativeRoot = Path.GetRelativePath(rootDir, workDir).Replace('\\', '/');
            if (relativeRoot is "." or "") relativeRoot = "";

            var graph = _scanner.ScanDirectory(workDir, label);
            graph.Meta.TerraformRoot = relativeRoot;
            var costs = _costs.Calculate(graph);
            var visualization = _layout.Build(graph, costs);

            return new ArchitectureScanResult
            {
                Graph = graph,
                Costs = costs,
                Visualization = visualization
            };
        }
        finally
        {
            if (cleanup)
            {
                try { Directory.Delete(rootDir, recursive: true); } catch { /* best effort */ }
            }
        }
    }

    private void EnsureAllowedLocal(string fullPath)
    {
        if (_allowedLocalRoots.Length == 0) return;
        if (_allowedLocalRoots.Any(root => fullPath.StartsWith(root, StringComparison.OrdinalIgnoreCase)))
            return;
        throw new UnauthorizedAccessException("localPath is outside allowed roots.");
    }
}
