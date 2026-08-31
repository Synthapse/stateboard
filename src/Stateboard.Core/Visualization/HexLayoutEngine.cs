using Stateboard.Core.Models;

namespace Stateboard.Core.Visualization;

/// <summary>
/// Packs infra nodes onto axial hexes in compact destination-group clusters.
/// </summary>
public sealed class HexLayoutEngine
{
    private static readonly string[] GroupOrder =
        ["compute", "database", "storage", "network", "identity", "generic"];

    private static readonly (int Q, int R)[] Spiral = BuildSpiral(24);

    public TerraformVisualization Build(InfraGraph graph, CostReport costs)
    {
        var costById = costs.Lines.ToDictionary(l => l.NodeId, l => l.MonthlyUsd, StringComparer.Ordinal);
        var byGroup = graph.Nodes
            .GroupBy(n => NormalizeGroup(n.SpriteKind), StringComparer.OrdinalIgnoreCase)
            .ToDictionary(g => g.Key, g => g.ToList(), StringComparer.OrdinalIgnoreCase);

        var groups = GroupOrder
            .Where(byGroup.ContainsKey)
            .Concat(byGroup.Keys.Where(k => !GroupOrder.Contains(k, StringComparer.OrdinalIgnoreCase)))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();

        var used = new HashSet<string>(StringComparer.Ordinal);
        var placements = new List<HexPlacement>();

        for (var gi = 0; gi < groups.Count; gi++)
        {
            var (cq, cr) = GroupCentroid(gi, groups.Count);
            var nodes = byGroup[groups[gi]]
                .OrderBy(n => n.ModulePath, StringComparer.Ordinal)
                .ThenBy(n => n.Address, StringComparer.Ordinal)
                .ToList();

            foreach (var node in nodes)
            {
                var slot = TakeSlot(cq, cr, used);
                if (slot is null) continue;
                placements.Add(new HexPlacement
                {
                    NodeId = node.Id,
                    Q = slot.Value.Q,
                    R = slot.Value.R,
                    Cloud = node.Cloud,
                    SpriteKind = NormalizeGroup(node.SpriteKind),
                    Address = node.Address,
                    MonthlyUsd = costById.GetValueOrDefault(node.Id)
                });
            }
        }

        var nodeIds = placements.Select(p => p.NodeId).ToHashSet(StringComparer.Ordinal);
        var edges = ResolveEdges(graph, nodeIds);
        var max = placements.Count == 0 ? 0 : placements.Max(p => p.MonthlyUsd);

        return new TerraformVisualization
        {
            Placements = placements,
            Edges = edges,
            MaxMonthlyUsd = max
        };
    }

    private static string NormalizeGroup(string spriteKind)
    {
        var k = (spriteKind ?? "generic").Trim().ToLowerInvariant();
        if (k is "data" or "db" or "database") return "database";
        if (k is "compute" or "network" or "storage" or "identity" or "generic") return k;
        return "generic";
    }

    private static List<DependencyEdge> ResolveEdges(InfraGraph graph, HashSet<string> placed)
    {
        var byModulePrefix = graph.Nodes
            .Where(n => !string.IsNullOrEmpty(n.ModulePath))
            .GroupBy(n => n.ModulePath.Split('/')[0], StringComparer.Ordinal)
            .ToDictionary(g => g.Key, g => g.Select(n => n.Id).ToList(), StringComparer.Ordinal);

        var edges = new HashSet<(string From, string To)>();
        foreach (var node in graph.Nodes)
        {
            if (!placed.Contains(node.Id)) continue;
            foreach (var dep in node.Dependencies)
            {
                if (placed.Contains(dep))
                {
                    edges.Add((node.Id, dep));
                    continue;
                }

                if (dep.StartsWith("module.", StringComparison.Ordinal))
                {
                    var modName = dep["module.".Length..].Split('.')[0];
                    if (byModulePrefix.TryGetValue(modName, out var ids))
                    {
                        var target = ids.FirstOrDefault(placed.Contains);
                        if (target is not null)
                            edges.Add((node.Id, target));
                    }
                }
            }
        }

        return edges.Select(e => new DependencyEdge { From = e.From, To = e.To }).ToList();
    }

    private static (int Q, int R)? TakeSlot(int cq, int cr, HashSet<string> used)
    {
        foreach (var (dq, dr) in Spiral)
        {
            var q = cq + dq;
            var r = cr + dr;
            var key = $"{q},{r}";
            if (!used.Add(key)) continue;
            return (q, r);
        }
        return null;
    }

    /// <summary>Compact ring so destination groups stay close but readable.</summary>
    private static (int Cq, int Cr) GroupCentroid(int index, int total)
    {
        if (total <= 1) return (0, 0);
        var angle = (index / (double)total) * Math.PI * 2 - Math.PI / 2;
        var dist = total <= 3 ? 2 : 3;
        return ((int)Math.Round(Math.Cos(angle) * dist), (int)Math.Round(Math.Sin(angle) * dist));
    }

    private static (int Q, int R)[] BuildSpiral(int maxRing)
    {
        var outList = new List<(int, int)> { (0, 0) };
        for (var ring = 1; ring <= maxRing; ring++)
        {
            var q = ring;
            var r = -ring;
            (int, int)[] dirs = [(0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1), (1, 0)];
            foreach (var (dq, dr) in dirs)
            {
                for (var i = 0; i < ring; i++)
                {
                    outList.Add((q, r));
                    q += dq;
                    r += dr;
                }
            }
        }
        return outList.ToArray();
    }
}
