import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useMemo, useState } from 'react';
import { calculateCosts, scanTfState, SAMPLE_TFSTATE } from '@stateboard/tf-cost';

export function StateboardPage() {
  const [raw, setRaw] = useState(() => JSON.stringify(SAMPLE_TFSTATE, null, 2));
  const [error, setError] = useState<string | null>(null);

  const result = useMemo(() => {
    try {
      const json = JSON.parse(raw) as unknown;
      const graph = scanTfState(json);
      // sync path for local books
      return { graph, costs: null as Awaited<ReturnType<typeof calculateCosts>> | null, err: null as string | null };
    } catch (e) {
      return { graph: null, costs: null, err: e instanceof Error ? e.message : 'Invalid JSON' };
    }
  }, [raw]);

  const [costs, setCosts] = useState<Awaited<ReturnType<typeof calculateCosts>> | null>(null);

  const runCost = async () => {
    setError(null);
    try {
      const json = JSON.parse(raw) as unknown;
      const graph = scanTfState(json);
      const report = await calculateCosts(graph, { priceSource: 'local' });
      setCosts(report);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Cost failed');
      setCosts(null);
    }
  };

  return (
    <div className="live-page" style={{ overflow: 'auto' }}>
      <div className="live-page-bar" style={{ pointerEvents: 'auto' }}>
        <Link to="/" className="live-page-back" aria-label="Back home">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <p className="live-page-title">Stateboard</p>
          <p className="live-page-sub">Scan state · cost module · map WIP</p>
        </div>
        <span className="live-page-badge">WIP</span>
      </div>

      <div style={{ padding: '5rem 1.25rem 2rem', maxWidth: 960, margin: '0 auto' }}>
        <p style={{ color: '#8f9097', marginTop: 0 }}>
          Paste <code>terraform.tfstate</code> JSON. Map rendering reuses the RTS lab; cost comes from{' '}
          <code>@stateboard/tf-cost</code>.
        </p>
        <textarea
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          rows={14}
          style={{
            width: '100%',
            fontFamily: 'ui-monospace, monospace',
            fontSize: 12,
            background: '#0d1c2d',
            color: '#d4e4fa',
            border: '1px solid #45474c',
            borderRadius: 8,
            padding: 12,
          }}
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
          <button type="button" className="home-btn" onClick={() => void runCost()}>
            Calculate costs
          </button>
          <Link className="home-btn home-btn--ghost" to="/live">
            Open RTS lab
          </Link>
        </div>
        {(error || result.err) && (
          <p style={{ color: '#ffb4ab' }}>{error ?? result.err}</p>
        )}
        {result.graph && (
          <p style={{ color: '#8f9097' }}>
            Scanned <strong style={{ color: '#d4e4fa' }}>{result.graph.nodes.length}</strong> nodes ·{' '}
            {result.graph.modules.length} modules
          </p>
        )}
        {costs && (
          <div
            style={{
              marginTop: 16,
              padding: 16,
              borderRadius: 8,
              border: '1px solid rgb(76 215 246 / 0.25)',
              background: 'rgb(5 20 36 / 0.9)',
            }}
          >
            <p style={{ margin: '0 0 8px', fontWeight: 600 }}>
              Estimate · ${costs.totalMonthlyUsd.toFixed(2)}/mo
            </p>
            <p style={{ margin: 0, color: '#8f9097', fontSize: 14 }}>
              AWS ${costs.byCloud.aws.toFixed(2)} · Azure ${costs.byCloud.azure.toFixed(2)} · GCP $
              {costs.byCloud.gcp.toFixed(2)} · other ${costs.byCloud.other.toFixed(2)}
            </p>
            <p style={{ margin: '8px 0 0', color: '#8f9097', fontSize: 12 }}>
              asOf {costs.asOf} · uncovered {costs.uncoveredCount}
              {costs.warnings.length ? ` · ${costs.warnings.join('; ')}` : ''}
            </p>
            <ul style={{ fontSize: 13, paddingLeft: 18 }}>
              {costs.lines.slice(0, 12).map((l) => (
                <li key={l.nodeId}>
                  {l.address}: ${l.monthlyUsd.toFixed(2)} ({l.confidence}) — {l.basis}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
