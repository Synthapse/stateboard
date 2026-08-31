using System.Diagnostics;
using System.Text.RegularExpressions;

namespace Stateboard.Core.Scanning;

public sealed class GitRepoFetcher
{
    private static readonly TimeSpan CloneTimeout = TimeSpan.FromMinutes(3);
    private static readonly Regex GithubShorthand = new(
        @"^(?:https?://)?(?:www\.)?github\.com/(?<owner>[^/\s]+)/(?<repo>[^/\s#?]+?)(?:\.git)?/?$",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex SymrefHead = new(
        @"ref:\s*refs/heads/(?<branch>[^\s\t]+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public async Task<string> CloneAsync(string gitUrl, string? gitRef = null, CancellationToken ct = default)
    {
        var url = NormalizeUrl(gitUrl);
        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri) ||
            (uri.Scheme != Uri.UriSchemeHttps && uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != "git"))
        {
            throw new ArgumentException("gitUrl must be an http(s) git repository URL (e.g. https://github.com/org/repo).");
        }

        var dir = Path.Combine(Path.GetTempPath(), "stateboard-clone", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(Path.GetDirectoryName(dir)!);

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(CloneTimeout);

        var requested = string.IsNullOrWhiteSpace(gitRef) ? null : gitRef.Trim();
        var defaultBranch = await TryResolveDefaultBranchAsync(url, cts.Token);

        // Prefer explicit ref → remote HEAD → omit --branch (git picks default).
        var candidates = new List<string?>();
        if (requested is not null) candidates.Add(requested);
        if (defaultBranch is not null &&
            !string.Equals(defaultBranch, requested, StringComparison.OrdinalIgnoreCase))
            candidates.Add(defaultBranch);
        candidates.Add(null); // last resort: no --branch

        Exception? last = null;
        foreach (var branch in candidates.Distinct(StringComparer.OrdinalIgnoreCase))
        {
            if (Directory.Exists(dir))
            {
                try { Directory.Delete(dir, recursive: true); } catch { /* ignore */ }
            }

            try
            {
                var branchArg = branch is null ? "" : $"--branch {Q(branch)} ";
                var args = $"clone --depth 1 --single-branch {branchArg}{Q(url)} {Q(dir)}";
                await RunGitAsync(args, cts.Token);
                return dir;
            }
            catch (InvalidOperationException ex) when (
                ex.Message.Contains("not found", StringComparison.OrdinalIgnoreCase) ||
                ex.Message.Contains("Remote branch", StringComparison.OrdinalIgnoreCase))
            {
                last = ex;
            }
        }

        throw last ?? new InvalidOperationException("git clone failed.");
    }

    public static string NormalizeUrl(string input)
    {
        var s = input.Trim();
        var m = GithubShorthand.Match(s);
        if (m.Success)
        {
            var repo = m.Groups["repo"].Value.TrimEnd('/');
            if (repo.EndsWith(".git", StringComparison.OrdinalIgnoreCase))
                repo = repo[..^4];
            return $"https://github.com/{m.Groups["owner"].Value}/{repo}.git";
        }
        return s.EndsWith(".git", StringComparison.OrdinalIgnoreCase) ? s : s;
    }

    private static async Task<string?> TryResolveDefaultBranchAsync(string url, CancellationToken ct)
    {
        try
        {
            var (stdout, stderr, code) = await RunGitCaptureAsync($"ls-remote --symref {Q(url)} HEAD", ct);
            var text = $"{stdout}\n{stderr}";
            var m = SymrefHead.Match(text);
            if (m.Success) return m.Groups["branch"].Value.Trim();
        }
        catch
        {
            // Best-effort — clone fallbacks still apply.
        }
        return null;
    }

    private static string Q(string value) =>
        $"\"{value.Replace("\"", "\\\"", StringComparison.Ordinal)}\"";

    private static async Task RunGitAsync(string args, CancellationToken ct)
    {
        var (_, stderr, code) = await RunGitCaptureAsync(args, ct);
        if (code != 0)
            throw new InvalidOperationException($"git clone failed: {stderr.Trim()}");
    }

    private static async Task<(string Stdout, string Stderr, int ExitCode)> RunGitCaptureAsync(
        string args, CancellationToken ct)
    {
        var psi = new ProcessStartInfo
        {
            FileName = "git",
            Arguments = args,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true
        };

        using var proc = Process.Start(psi)
            ?? throw new InvalidOperationException("Failed to start git.");

        var stderrTask = proc.StandardError.ReadToEndAsync(ct);
        var stdoutTask = proc.StandardOutput.ReadToEndAsync(ct);
        try
        {
            await proc.WaitForExitAsync(ct);
        }
        catch (OperationCanceledException)
        {
            try { proc.Kill(entireProcessTree: true); } catch { /* ignore */ }
            throw new TimeoutException("git timed out.");
        }

        return (await stdoutTask, await stderrTask, proc.ExitCode);
    }
}

/// <summary>Finds a sensible Terraform root when the caller does not specify one.</summary>
public static class TerraformRootFinder
{
    public static string Resolve(string repoRoot, string? preferredRelative)
    {
        if (!string.IsNullOrWhiteSpace(preferredRelative))
        {
            var explicitPath = Path.GetFullPath(Path.Combine(repoRoot, preferredRelative));
            if (!Directory.Exists(explicitPath))
                throw new DirectoryNotFoundException($"Terraform root not found: {preferredRelative}");
            return explicitPath;
        }

        // Prefer repo root if it has .tf files.
        if (Directory.EnumerateFiles(repoRoot, "*.tf", SearchOption.TopDirectoryOnly).Any())
            return repoRoot;

        // Common layouts
        foreach (var candidate in new[] { "terraform", "infra", "infrastructure", "tf", "deploy/terraform" })
        {
            var path = Path.Combine(repoRoot, candidate);
            if (Directory.Exists(path) &&
                Directory.EnumerateFiles(path, "*.tf", SearchOption.AllDirectories)
                    .Any(p => !p.Contains($"{Path.DirectorySeparatorChar}.terraform{Path.DirectorySeparatorChar}")))
                return path;
        }

        // Directory with the most .tf files
        var best = Directory
            .EnumerateFiles(repoRoot, "*.tf", SearchOption.AllDirectories)
            .Where(p => !p.Contains($"{Path.DirectorySeparatorChar}.terraform{Path.DirectorySeparatorChar}"))
            .Select(p => Path.GetDirectoryName(p)!)
            .GroupBy(d => d, StringComparer.OrdinalIgnoreCase)
            .OrderByDescending(g => g.Count())
            .FirstOrDefault();

        if (best is null)
            throw new InvalidOperationException("No .tf files found in the repository.");

        return best.Key;
    }
}
