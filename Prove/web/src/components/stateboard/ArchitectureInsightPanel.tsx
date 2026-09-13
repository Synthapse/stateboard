import { RefreshCw, Sparkles, X } from 'lucide-react';
import type { ArchitectureAnalysis } from '../../api';

type Props = {
  analysis: ArchitectureAnalysis | null;
  busy: boolean;
  error: string | null;
  onRefresh: () => void;
  onClose: () => void;
};

export function ArchitectureInsightPanel({ analysis, busy, error, onRefresh, onClose }: Props) {
  return (
    <aside className="sb-insight-panel" role="dialog" aria-label="Architecture insight">
      <div className="sb-insight-panel-head">
        <div className="sb-insight-title">
          <Sparkles size={14} aria-hidden />
          <h2>Architecture insight</h2>
        </div>
        <div className="sb-insight-panel-actions">
          <button
            type="button"
            className="sb-icon-btn"
            onClick={onRefresh}
            disabled={busy}
            aria-label="Refresh analysis"
            title="Refresh analysis"
          >
            <RefreshCw size={14} className={busy ? 'sb-spin' : undefined} />
          </button>
          <button
            type="button"
            className="sb-icon-btn"
            aria-label="Close architecture insight"
            onClick={onClose}
          >
            <X size={16} />
          </button>
        </div>
      </div>

      <div className="sb-insight-panel-body">
        <p className="sb-insight-lead">
          GenAI read of purpose, improvements, and how to split this estate into Terraform modules.
        </p>

        {busy && !analysis && <p className="sb-insight-status">Analyzing estate with GenAI…</p>}
        {error && <p className="sb-insight-error">{error}</p>}

        {analysis && (
          <>
            <div className="sb-insight-block">
              <p className="sb-explain-k">Purpose</p>
              <p className="sb-insight-purpose">{analysis.purpose}</p>
            </div>

            <div className="sb-insight-block">
              <p className="sb-explain-k">What it supports / holds</p>
              <p className="sb-explain-v">{analysis.supports}</p>
            </div>

            {(analysis.improvements?.length ?? 0) > 0 && (
              <div className="sb-insight-block">
                <p className="sb-explain-k">How it may be improved</p>
                <ul className="sb-insight-list sb-insight-list--improve">
                  {analysis.improvements.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {(analysis.moduleSplits?.length ?? 0) > 0 && (
              <div className="sb-insight-block">
                <p className="sb-explain-k">Suggested module splits</p>
                <ul className="sb-insight-list sb-insight-list--modules">
                  {analysis.moduleSplits.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.workloads.length > 0 && (
              <div className="sb-insight-block">
                <p className="sb-explain-k">Workloads</p>
                <ul className="sb-insight-list">
                  {analysis.workloads.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.capabilities.length > 0 && (
              <div className="sb-insight-block">
                <p className="sb-explain-k">Capabilities</p>
                <ul className="sb-insight-list">
                  {analysis.capabilities.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.risks.length > 0 && (
              <div className="sb-insight-block">
                <p className="sb-explain-k">Watch-outs</p>
                <ul className="sb-insight-list sb-insight-list--risk">
                  {analysis.risks.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.summary && (
              <div className="sb-insight-block">
                <p className="sb-explain-k">Summary</p>
                <p className="sb-explain-v">{analysis.summary}</p>
              </div>
            )}

            <p className="sb-insight-meta">
              {analysis.source === 'gemini'
                ? `Gemini · ${analysis.model || 'model'}`
                : analysis.configured
                  ? `Fallback · ${analysis.source}`
                  : 'Local heuristic — set GEMINI_API_KEY for Gemini'}
            </p>
          </>
        )}

        {!busy && !analysis && !error && (
          <p className="sb-insight-status">No analysis yet. Refresh after a successful scan.</p>
        )}
      </div>
    </aside>
  );
}
