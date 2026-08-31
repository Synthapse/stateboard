namespace Stateboard.Core.Models;

public enum Cloud
{
    Aws,
    Azure,
    Gcp,
    Other
}

public enum CostFamily
{
    Compute,
    Disk,
    Object,
    Database,
    Network,
    Free,
    Other
}

public enum SpriteKind
{
    Compute,
    Network,
    Storage,
    Database,
    Identity,
    Generic
}

public sealed class CostAttrs
{
    public string? Region { get; set; }
    public string? Sku { get; set; }
    public double? StorageGb { get; set; }
    public bool? MultiAz { get; set; }
}

public sealed class InfraNode
{
    public required string Id { get; set; }
    public required string Address { get; set; }
    public required string Type { get; set; }
    public required string Name { get; set; }
    public required string Cloud { get; set; }
    public required string Provider { get; set; }
    public required string ModulePath { get; set; }
    public List<string> Dependencies { get; set; } = [];
    public CostAttrs Attrs { get; set; } = new();
    public required string SpriteKind { get; set; }
}

public sealed class InfraModule
{
    public required string Path { get; set; }
    public List<string> NodeIds { get; set; } = [];
}

public sealed class InfraGraph
{
    public required InfraMeta Meta { get; set; }
    public List<InfraNode> Nodes { get; set; } = [];
    public List<InfraModule> Modules { get; set; } = [];
}

public sealed class InfraMeta
{
    public string TerraformVersion { get; set; } = "hcl-scan";
    public int Serial { get; set; }
    public string? Lineage { get; set; }
    public string? Source { get; set; }
    public string? TerraformRoot { get; set; }
}

public sealed class UnitPrice
{
    public double Amount { get; set; }
    public string Unit { get; set; } = "month";
    public string Source { get; set; } = "pricebook";
    public string AsOf { get; set; } = "";
}

public sealed class CostLine
{
    public required string NodeId { get; set; }
    public required string Address { get; set; }
    public required string Cloud { get; set; }
    public required string Family { get; set; }
    public double MonthlyUsd { get; set; }
    public string Confidence { get; set; } = "unknown";
    public string Basis { get; set; } = "";
    public UnitPrice? UnitPrice { get; set; }
}

public sealed class CostReport
{
    public required string AsOf { get; set; }
    public string Currency { get; set; } = "USD";
    public double HoursPerMonth { get; set; } = 730;
    public double TotalMonthlyUsd { get; set; }
    public required Dictionary<string, double> ByCloud { get; set; }
    public List<ModuleCost> ByModule { get; set; } = [];
    public List<TypeCost> ByType { get; set; } = [];
    public Dictionary<string, double> ByFamily { get; set; } = [];
    public List<CostLine> Lines { get; set; } = [];
    public int UncoveredCount { get; set; }
    public List<string> Warnings { get; set; } = [];
}

public sealed class ModuleCost
{
    public required string Path { get; set; }
    public double MonthlyUsd { get; set; }
    public int NodeCount { get; set; }
}

public sealed class TypeCost
{
    public required string Type { get; set; }
    public double MonthlyUsd { get; set; }
    public int NodeCount { get; set; }
}

/// <summary>Hex board placement for one Terraform resource.</summary>
public sealed class HexPlacement
{
    public required string NodeId { get; set; }
    public int Q { get; set; }
    public int R { get; set; }
    public required string Cloud { get; set; }
    public required string SpriteKind { get; set; }
    public required string Address { get; set; }
    public double MonthlyUsd { get; set; }
}

public sealed class DependencyEdge
{
    public required string From { get; set; }
    public required string To { get; set; }
}

/// <summary>Ready-to-draw terraform architecture for the RTS map.</summary>
public sealed class TerraformVisualization
{
    public List<HexPlacement> Placements { get; set; } = [];
    public List<DependencyEdge> Edges { get; set; } = [];
    public double MaxMonthlyUsd { get; set; }
}

public sealed class ArchitectureScanResult
{
    public required InfraGraph Graph { get; set; }
    public required CostReport Costs { get; set; }
    public required TerraformVisualization Visualization { get; set; }
}
