import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import {
  calculateCosts,
  scanTfState,
  SAMPLE_TFSTATE,
  type CostReport,
  type HexPlacement,
  type InfraGraph,
} from '@stateboard/tf-cost';
import { StateboardMapView } from '../components/stateboard/StateboardMapView';

export function StateboardPage() {
  const [raw, setRaw] = useState(() => JSON.stringify(SAMPLE_TFSTATE, null, 2));
  const [graph, setGraph] = useState<InfraGraph | null>(null);
  const [costs, setCosts] = useState<CostReport | null>(null);
  const [selected, setSelected] = useState<HexPlacement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const run = useCallback(async (source: string) => {
    setBusy(true);
    setError(null);
    try {
      const json = JSON.parse(source) as unknown;
      const g = scanTfState(json);
      const report = await calculateCosts(g, { priceSource: 'local' });
      setGraph(g);
      setCosts(report);
      setSelected(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to scan / cost');
      setGraph(null);
      setCosts(null);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void run(raw);
    // initial sample only once
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onFile = async (file: File | null) => {
    if (!file) return;
    const text = await file.text();
    setRaw(text);
    await run(text);
  };

  const line = costs?.lines.find((l) => l.nodeId === selected?.nodeId);

  return (
    <div className="live-page">
      <div className="live-page-bar">
        <Link to="/" className="live-page-back" aria-label="Back home">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <p className="live-page-title">Stateboard</p>
          <p className="live-page-sub">
            {costs
              ? `$${costs.totalMonthlyUsd.toFixed(0)}/mo · AWS $${costs.byCloud.aws.toFixed(0)} · Azure $${costs.byCloud.azure.toFixed(0)} · GCP $${costs.byCloud.gcp.toFixed(0)}`
              : 'Scan state · draw estate · calculate cost'}
          </p>
        </div>
        <button
          type="button"
          className="live-page-badge"
          style={{ cursor: 'pointer', border: 'none' }}
          onClick={() => setPanelOpen((v) => !v)}
        >
          {panelOpen ? 'Hide' : 'State'}
        </button>
      </div>

      {graph && costs ? (
        <StateboardMapView graph={graph} costs={costs} onSelect={setSelected} />
      ) : (
        <div className="live-sandbox-wrap" style={{ display: 'grid', placeItems: 'center' }}>
          <p style={{ color: '#8f9097' }}>{busy ? 'Scanning…' : 'Load a terraform.tfstate'}</p>
        </div>
      )}

      <div className="live-sandbox-hud">
        <div className="live-sandbox-resources">
          <span>{graph ? `${graph.nodes.length} resources` : '—'}</span>
          <span>{graph ? `${graph.modules.length} modules` : '—'}</span>
          {costs && <span>uncovered {costs.uncoveredCount}</span>}
          {costs && <span className="live-sandbox-timer">${costs.totalMonthlyUsd.toFixed(2)}/mo</span>}
        </div>
        {selected ? (
          <p className="live-sandbox-selection">
            {selected.address}
            <span className="live-sandbox-team"> · {selected.cloud}</span>
            <span>
              {' '}
              · ${selected.monthlyUsd.toFixed(2)}/mo
              {line ? ` · ${line.basis}` : ''}
            </span>
          </p>
        ) : (
          <p className="live-sandbox-selection live-sandbox-selection--muted">
            Click a resource sprite · cost bar = relative $/mo
          </p>
        )}
      </div>

      {panelOpen && (
        <div
          style={{
            position: 'absolute',
            top: '4.5rem',
            right: '0.75rem',
            zIndex: 30,
            width: 'min(380px, calc(100vw - 1.5rem))',
            maxHeight: 'calc(100dvh - 8rem)',
            overflow: 'auto',
            padding: '0.85rem',
            borderRadius: '0.75rem',
            border: '1px solid rgb(76 215 246 / 0.22)',
            background: 'rgb(5 20 36 / 0.92)',
            backdropFilter: 'blur(12px)',
          }}
        >
          <label style={{ display: 'block', fontSize: 12, color: '#8f9097', marginBottom: 6 }}>
            Upload .tfstate
          </label>
          <input
            type="file"
            accept=".json,application/json,.tfstate"
            onChange={(e) => void onFile(e.target.files?.[0] ?? null)}
            style={{ color: '#d4e4fa', fontSize: 12, marginBottom: 10, width: '100%' }}
          />
          <textarea
            value={raw}
            onChange={(e) => setRaw(e.target.value)}
            rows={10}
            style={{
              width: '100%',
              fontFamily: 'ui-monospace, monospace',
              fontSize: 11,
              background: '#0d1c2d',
              color: '#d4e4fa',
              border: '1px solid #45474c',
              borderRadius: 8,
              padding: 8,
            }}
          />
          <button
            type="button"
            className="home-btn"
            style={{ marginTop: 10, width: '100%', justifyContent: 'center' }}
            disabled={busy}
            onClick={() => void run(raw)}
          >
            {busy ? 'Working…' : 'Scan + calculate'}
          </button>
          {error && <p style={{ color: '#ffb4ab', fontSize: 13 }}>{error}</p>}
          {costs && (
            <ul style={{ fontSize: 12, paddingLeft: 16, color: '#8f9097' }}>
              {costs.byModule.map((m) => (
                <li key={m.path || 'root'}>
                  {m.path || '(root)'}: ${m.monthlyUsd.toFixed(2)} ({m.nodeCount})
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
