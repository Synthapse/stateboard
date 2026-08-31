using Stateboard.Core;
using Stateboard.Core.Cost;
using Stateboard.Core.GenAI;
using Stateboard.Core.Models;
using Stateboard.Core.Scanning;

namespace Stateboard.Tests;

public class PipelineTests
{
    [Fact]
    public async Task SampleFixture_ProducesGraphCostsAndVisualization()
    {
        var fixtures = FindFixtures();
        var svc = new ArchitectureService(fixtures);
        var result = await svc.ScanAsync(new ScanRequest { Fixture = "sample" });

        Assert.True(result.Graph.Nodes.Count >= 5);
        Assert.True(result.Costs.TotalMonthlyUsd > 0);
        Assert.Equal(result.Graph.Nodes.Count, result.Visualization.Placements.Count);
        Assert.Contains(result.Visualization.Edges, e => e.From == "aws_volume_attachment.data");
        Assert.Contains(result.Graph.Nodes, n => n.Type == "aws_db_instance" && n.SpriteKind == "database");
    }

    [Fact]
    public void CostModule_ClassifiesDbInstanceAsDatabase()
    {
        Assert.Equal(CostFamily.Database, FamilyClassifier.Classify("aws_db_instance"));
        Assert.Equal(CostFamily.Compute, FamilyClassifier.Classify("aws_instance"));
        Assert.Equal(CostFamily.Compute, FamilyClassifier.Classify("azurerm_linux_virtual_machine"));
        Assert.Equal(CostFamily.Free, FamilyClassifier.Classify("google_compute_network"));
        Assert.Equal(CostFamily.Network, FamilyClassifier.Classify("google_compute_forwarding_rule"));
        Assert.Equal(CostFamily.Free, FamilyClassifier.Classify("google_service_account"));
        Assert.Equal(CostFamily.Free, FamilyClassifier.Classify("google_secret_manager_secret_version"));
        Assert.Equal(CostFamily.Free, FamilyClassifier.Classify("google_artifact_registry_repository"));
        Assert.Equal(CostFamily.Free, FamilyClassifier.Classify("google_cloud_tasks_queue"));
        Assert.Equal(SpriteKind.Identity, SpriteMapping.FromType("google_service_account"));
        Assert.Equal(SpriteKind.Identity, SpriteMapping.FromType("google_secret_manager_secret_version"));
        Assert.Equal(SpriteKind.Identity, SpriteMapping.FromType("google_storage_bucket_iam_member"));
        Assert.Equal(SpriteKind.Storage, SpriteMapping.FromType("google_storage_bucket"));
        Assert.Equal(SpriteKind.Storage, SpriteMapping.FromType("google_artifact_registry_repository"));
        Assert.Equal(SpriteKind.Compute, SpriteMapping.FromType("google_cloud_tasks_queue"));
        Assert.Equal(SpriteKind.Compute, SpriteMapping.FromType("google_cloud_scheduler_job"));
        Assert.Equal(SpriteKind.Compute, SpriteMapping.FromType("google_cloud_run_v2_service"));
        Assert.Equal(SpriteKind.Compute, SpriteMapping.FromType("google_cloud_run_v2_job"));
        Assert.Equal(SpriteKind.Identity, SpriteMapping.FromType("google_cloud_run_v2_service_iam_member"));
        Assert.Equal(SpriteKind.Generic, SpriteMapping.FromType("google_project_service"));
        Assert.Equal(SpriteKind.Generic, SpriteMapping.FromType("random_id"));
        Assert.Equal(SpriteKind.Identity, SpriteMapping.FromType("random_password"));
        Assert.Equal(SpriteKind.Network, SpriteMapping.FromType("google_compute_network"));
    }

    [Fact]
    public void CostModule_PricesAzureVmWithDefaults()
    {
        var prices = new PriceBookStore(Path.Combine(FindFixtures(), "..", "src", "Stateboard.Core", "Pricebooks"));
        var module = new CostCalculationModule(prices);
        var graph = new InfraGraph
        {
            Meta = new InfraMeta(),
            Nodes =
            [
                new InfraNode
                {
                    Id = "azurerm_linux_virtual_machine.app",
                    Address = "azurerm_linux_virtual_machine.app",
                    Type = "azurerm_linux_virtual_machine",
                    Name = "app",
                    Cloud = "azure",
                    Provider = "azurerm",
                    ModulePath = "",
                    SpriteKind = "compute",
                    Attrs = new CostAttrs { Sku = "Standard_D2s_v3", Region = "eastus" }
                }
            ]
        };
        var report = module.Calculate(graph);
        Assert.True(report.TotalMonthlyUsd > 0);
        Assert.Equal(0, report.UncoveredCount);
    }

    [Fact]
    public void GitUrl_NormalizesGithub()
    {
        Assert.Equal(
            "https://github.com/hashicorp/terraform-provider-aws.git",
            GitRepoFetcher.NormalizeUrl("https://github.com/hashicorp/terraform-provider-aws"));
    }

    [Fact]
    public void GenAI_Heuristic_DescribesSampleLikeStack()
    {
        var graph = new InfraGraph
        {
            Meta = new InfraMeta { Source = "test" },
            Nodes =
            [
                new InfraNode
                {
                    Id = "aws_instance.web", Address = "aws_instance.web", Type = "aws_instance",
                    Name = "web", Cloud = "aws", Provider = "aws", ModulePath = "", SpriteKind = "compute"
                },
                new InfraNode
                {
                    Id = "aws_db_instance.app", Address = "aws_db_instance.app", Type = "aws_db_instance",
                    Name = "app", Cloud = "aws", Provider = "aws", ModulePath = "", SpriteKind = "database"
                }
            ]
        };
        var costs = new CostCalculationModule(
            new PriceBookStore(Path.Combine(FindFixtures(), "..", "src", "Stateboard.Core", "Pricebooks")))
            .Calculate(graph);
        var analysis = ArchitectureAnalysisModule.HeuristicAnalyze(graph, costs);
        Assert.False(string.IsNullOrWhiteSpace(analysis.Purpose));
        Assert.False(string.IsNullOrWhiteSpace(analysis.Supports));
        Assert.Contains(analysis.Workloads, w =>
            w.Contains("Web", StringComparison.OrdinalIgnoreCase) ||
            w.Contains("API", StringComparison.OrdinalIgnoreCase));
    }

    private static string FindFixtures()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var fixtures = Path.Combine(dir.FullName, "fixtures");
            if (Directory.Exists(fixtures)) return fixtures;
            dir = dir.Parent;
        }
        throw new DirectoryNotFoundException("fixtures");
    }
}
