import { Link } from 'react-router-dom';
import { ArrowLeft, Layers, Settings, Sparkles } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import type { CostReport, HexPlacement, InfraGraph } from '@stateboard/tf-cost';
import {
  analyzeArchitecture,
  scanArchitecture,
  scanSample,
  type ArchitectureAnalysis,
  type ArchitectureScanResult,
  type TerraformVisualization,
} from '../api';
import { ArchitectureInsightPanel } from '../components/stateboard/ArchitectureInsightPanel';
import { SelectedResourcePanel } from '../components/stateboard/SelectedResourcePanel';
import { SettingsPanel } from '../components/stateboard/SettingsPanel';
import { StateboardMapView } from '../components/stateboard/StateboardMapView';
import { StructureInspector } from '../components/stateboard/StructureInspector';

type SidePanel = 'structure' | 'insight' | 'settings' | null;

export function StateboardPage() {
  const [gitUrl, setGitUrl] = useState('');
  const [gitRef, setGitRef] = useState('');
  const [terraformRoot, setTerraformRoot] = useState('');
  const [graph, setGraph] = useState<InfraGraph | null>(null);
  const [costs, setCosts] = useState<CostReport | null>(null);
  const [viz, setViz] = useState<TerraformVisualization | null>(null);
  const [selected, setSelected] = useState<HexPlacement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [panel, setPanel] = useState<SidePanel>(null);
  const [busy, setBusy] = useState(false);
  const [sourceLabel, setSourceLabel] = useState('fixture:sample');
  const [analysis, setAnalysis] = useState<ArchitectureAnalysis | null>(null);
  const [analysisBusy, setAnalysisBusy] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const runAnalysis = useCallback(async (g: InfraGraph, c: CostReport) => {
    setAnalysisBusy(true);
    setAnalysisError(null);
    try {
      const result = await analyzeArchitecture(g, c);
      setAnalysis(result);
    } catch (e) {
      setAnalysis(null);
      setAnalysisError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setAnalysisBusy(false);
    }
  }, []);

  const apply = useCallback(async (label: string, run: () => Promise<ArchitectureScanResult>) => {
    setBusy(true);
    setError(null);
    setAnalysis(null);
    setAnalysisError(null);
    try {
      const result = await run();
      setGraph(result.graph);
      setCosts(result.costs);
      setViz(result.visualization);
      setSourceLabel(label);
      setSelected(null);
      setPanel(null);
      void runAnalysis(result.graph, result.costs);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Scan failed');
      setGraph(null);
      setCosts(null);
      setViz(null);
      setAnalysis(null);
    } finally {
      setBusy(false);
    }
  }, [runAnalysis]);

  useEffect(() => {
    void apply('fixture:sample', () => scanSample());
  }, [apply]);

  const onScanRepo = () => {
    if (!gitUrl.trim()) {
      setError('Paste a git HTTPS URL of a Terraform repo.');
      return;
    }
    void apply(gitUrl.trim(), () =>
      scanArchitecture({
        gitUrl: gitUrl.trim(),
        ref: gitRef.trim() || undefined,
        terraformRoot: terraformRoot.trim() || undefined,
      }),
    );
  };

  const onSelectNode = (nodeId: string) => {
    const p = viz?.placements.find((x) => x.nodeId === nodeId) ?? null;
    setSelected(p);
  };

  const togglePanel = (next: SidePanel) => {
    setPanel((cur) => (cur === next ? null : next));
  };

  const ready = Boolean(graph && costs);

  return (
    <div className="live-page">
      <nav className="sb-rail" aria-label="Map tools">
        <button
          type="button"
          className={`sb-rail-btn${panel === 'structure' ? ' sb-rail-btn--active' : ''}`}
          aria-label="Structure"
          aria-expanded={panel === 'structure'}
          title="Structure"
          disabled={!ready}
          onClick={() => togglePanel('structure')}
        >
          <Layers size={18} />
        </button>
        <button
          type="button"
          className={`sb-rail-btn${panel === 'insight' ? ' sb-rail-btn--active' : ''}`}
          aria-label="Architecture insight"
          aria-expanded={panel === 'insight'}
          title="Architecture insight (AI)"
          disabled={!ready}
          onClick={() => togglePanel('insight')}
        >
          <Sparkles size={18} />
        </button>
        <span className="sb-rail-sep" aria-hidden />
        <button
          type="button"
          className={`sb-rail-btn${panel === 'settings' ? ' sb-rail-btn--active' : ''}`}
          aria-label="Settings"
          aria-expanded={panel === 'settings'}
          title="Settings"
          onClick={() => togglePanel('settings')}
        >
          <Settings size={18} />
        </button>
      </nav>

      <Link to="/" className="sb-back" aria-label="Back home">
        <ArrowLeft size={18} />
      </Link>

      {viz && graph && viz.placements.length > 0 ? (
        <StateboardMapView
          visualization={viz}
          graph={graph}
          selectedId={selected?.nodeId ?? null}
          onSelect={setSelected}
        />
      ) : (
        <div className="live-sandbox-wrap" style={{ display: 'grid', placeItems: 'center' }}>
          <p style={{ color: '#8f9097' }}>{busy ? 'Cloning & scanning…' : 'Loading architecture…'}</p>
        </div>
      )}

      {panel === 'structure' && graph && costs && (
        <StructureInspector
          graph={graph}
          costs={costs}
          selectedId={selected?.nodeId ?? null}
          sourceLabel={sourceLabel}
          onSelectNode={onSelectNode}
          onClose={() => setPanel(null)}
        />
      )}

      {panel === 'insight' && (
        <ArchitectureInsightPanel
          analysis={analysis}
          busy={analysisBusy}
          error={analysisError}
          onRefresh={() => {
            if (graph && costs) void runAnalysis(graph, costs);
          }}
          onClose={() => setPanel(null)}
        />
      )}

      {panel === 'settings' && (
        <SettingsPanel
          gitUrl={gitUrl}
          gitRef={gitRef}
          terraformRoot={terraformRoot}
          busy={busy}
          error={error}
          onGitUrl={setGitUrl}
          onGitRef={setGitRef}
          onTerraformRoot={setTerraformRoot}
          onScanRepo={onScanRepo}
          onSample={() => void apply('fixture:sample', () => scanSample())}
          onClose={() => setPanel(null)}
        />
      )}

      {selected && graph && costs && (
        <SelectedResourcePanel
          graph={graph}
          costs={costs}
          selectedId={selected.nodeId}
          onSelectNode={onSelectNode}
          onClose={() => setSelected(null)}
        />
      )}

      <div className="sb-hud">
        <div className="sb-hud-row">
          <span>{graph ? `${graph.nodes.length} resources` : '—'}</span>
          <span>{graph ? `${graph.modules.length} modules` : '—'}</span>
          <span>{viz ? `${viz.edges.length} deps` : '—'}</span>
          {costs && <span className="sb-hud-cost">${costs.totalMonthlyUsd.toFixed(2)}/mo</span>}
        </div>
      </div>
    </div>
  );
}
