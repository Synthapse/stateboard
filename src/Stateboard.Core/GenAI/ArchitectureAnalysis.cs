namespace Stateboard.Core.GenAI;

public sealed class GeminiOptions
{
    public string ApiKey { get; set; } = "";
    public string Model { get; set; } = "gemini-3.6-flash";
    public string ApiBase { get; set; } = "https://generativelanguage.googleapis.com/v1beta";
}

/// <summary>LLM insight about what an infra estate is for and what it can support.</summary>
public sealed class ArchitectureAnalysis
{
    public required string Purpose { get; set; }
    public required string Supports { get; set; }
    public List<string> Capabilities { get; set; } = [];
    public List<string> Workloads { get; set; } = [];
    public List<string> Risks { get; set; } = [];
    public List<string> Improvements { get; set; } = [];
    public List<string> ModuleSplits { get; set; } = [];
    public string Summary { get; set; } = "";
    public string Model { get; set; } = "";
    public string Source { get; set; } = "gemini";
    public bool Configured { get; set; } = true;
}
