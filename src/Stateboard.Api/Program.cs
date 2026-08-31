using System.Text.Json;
using System.Text.Json.Serialization;
using Stateboard.Core;
using Stateboard.Core.Cost;
using Stateboard.Core.GenAI;
using Stateboard.Core.Models;

var builder = WebApplication.CreateBuilder(args);

builder.Configuration.AddJsonFile("appsettings.Local.json", optional: true, reloadOnChange: true);

builder.Services.ConfigureHttpJsonOptions(o =>
{
    o.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
    o.SerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
});

builder.Services.AddCors(o =>
{
    o.AddDefaultPolicy(p => p
        .WithOrigins(CorsOrigins(builder.Configuration))
        .AllowAnyHeader()
        .AllowAnyMethod());
});

builder.Services.AddHttpClient();

var repoRoot = FindRepoRoot(builder.Environment.ContentRootPath);
var fixturesRoot = Path.Combine(repoRoot, "fixtures");
var allowedRoots = new List<string> { fixturesRoot, repoRoot };
if (builder.Configuration["Scan:ExtraAllowedRoot"] is { Length: > 0 } extra)
    allowedRoots.Add(extra);

var pricebooksDir = Path.Combine(AppContext.BaseDirectory, "Pricebooks");
if (!Directory.Exists(pricebooksDir))
    pricebooksDir = Path.Combine(repoRoot, "src", "Stateboard.Core", "Pricebooks");

var gemini = new GeminiOptions
{
    ApiKey = Environment.GetEnvironmentVariable("GEMINI_API_KEY")
             ?? builder.Configuration["Gemini:ApiKey"]
             ?? "",
    Model = builder.Configuration["Gemini:Model"] ?? "gemini-3.6-flash",
    ApiBase = builder.Configuration["Gemini:ApiBase"]
              ?? "https://generativelanguage.googleapis.com/v1beta"
};

builder.Services.AddSingleton(new PriceBookStore(pricebooksDir));
builder.Services.AddSingleton(sp => new CostCalculationModule(sp.GetRequiredService<PriceBookStore>()));
builder.Services.AddSingleton(sp =>
    new ArchitectureService(fixturesRoot, allowedRoots, sp.GetRequiredService<CostCalculationModule>()));
builder.Services.AddSingleton(gemini);
builder.Services.AddSingleton(sp =>
    new ArchitectureAnalysisModule(
        sp.GetRequiredService<GeminiOptions>(),
        sp.GetRequiredService<IHttpClientFactory>().CreateClient()));

var app = builder.Build();
app.UseCors();

app.MapGet("/api/health", (ArchitectureAnalysisModule genai) => Results.Ok(new
{
    ok = true,
    service = "stateboard-api",
    modules = new[] { "scan", "cost", "visualization", "genai" },
    genai = new { configured = genai.IsConfigured, provider = "gemini" }
}));

app.MapPost("/api/architecture/scan", async (ScanRequest body, ArchitectureService svc, CancellationToken ct) =>
{
    try
    {
        var result = await svc.ScanAsync(body, ct);
        return Results.Ok(result);
    }
    catch (Exception ex) when (
        ex is ArgumentException or DirectoryNotFoundException or InvalidOperationException
            or UnauthorizedAccessException or TimeoutException)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
});

app.MapGet("/api/architecture/sample", async (ArchitectureService svc, CancellationToken ct) =>
{
    var result = await svc.ScanAsync(new ScanRequest { Fixture = "sample" }, ct);
    return Results.Ok(result);
});

/// <summary>GenAI module: Gemini analysis of architecture purpose and what it supports.</summary>
app.MapPost("/api/architecture/analyze", async (
    AnalyzeRequest body,
    ArchitectureAnalysisModule genai,
    CostCalculationModule costModule,
    CancellationToken ct) =>
{
    if (body.Graph is null)
        return Results.BadRequest(new { error = "graph is required" });

    var costs = body.Costs ?? costModule.Calculate(body.Graph);
    var analysis = await genai.AnalyzeAsync(body.Graph, costs, ct);
    return Results.Ok(analysis);
});

/// <summary>Cost-only recalculation for an already-scanned graph (testing / clients).</summary>
app.MapPost("/api/cost/calculate", (InfraGraphBody body, CostCalculationModule costs) =>
{
    if (body.Graph is null)
        return Results.BadRequest(new { error = "graph is required" });
    return Results.Ok(costs.Calculate(body.Graph, body.HoursPerMonth ?? 730));
});

app.Run();

static string FindRepoRoot(string start)
{
    var dir = new DirectoryInfo(start);
    while (dir is not null)
    {
        if (File.Exists(Path.Combine(dir.FullName, "Stateboard.sln")) ||
            Directory.Exists(Path.Combine(dir.FullName, "fixtures")))
            return dir.FullName;
        dir = dir.Parent;
    }
    return start;
}

static string[] CorsOrigins(IConfiguration config)
{
    var fromEnv = Environment.GetEnvironmentVariable("CORS_ALLOWED_ORIGINS");
    if (!string.IsNullOrWhiteSpace(fromEnv))
        return fromEnv.Split(',', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);

    var fromConfig = config.GetSection("Cors:AllowedOrigins").Get<string[]>();
    if (fromConfig is { Length: > 0 })
        return fromConfig;

    return ["http://localhost:5173", "http://127.0.0.1:5173"];
}

sealed class InfraGraphBody
{
    public InfraGraph? Graph { get; set; }
    public double? HoursPerMonth { get; set; }
}

sealed class AnalyzeRequest
{
    public InfraGraph? Graph { get; set; }
    public CostReport? Costs { get; set; }
}
