import { X } from 'lucide-react';
import { useMemo } from 'react';
import type { CostReport, InfraGraph, InfraNode } from '@stateboard/tf-cost';
import { explainResource } from './resourceExplain';
import { GROUP_META, GROUP_ORDER, type ResourceGroup } from './resourceGroups';
import { tfSpriteDataUrl } from './tfSprites';

type Props = {
  graph: InfraGraph;
  costs: CostReport;
  selectedId: string;
  onSelectNode: (nodeId: string) => void;
  onClose: () => void;
};

function moduleLabel(path: string) {
  return path ? `module.${path}` : 'root';
}

function resolveDepId(graph: InfraGraph, dep: string): string | null {
  const exact = graph.nodes.find((n) => n.id === dep || n.address === dep);
  if (exact) return exact.id;
  if (dep.startsWith('module.')) {
    const mod = dep.slice('module.'.length).split('.')[0];
    const hit = graph.nodes.find(
      (n) => n.modulePath === mod || n.modulePath.startsWith(`${mod}/`),
    );
    return hit?.id ?? null;
  }
  return null;
}

function groupOf(node: InfraNode): ResourceGroup {
  return (GROUP_ORDER.includes(node.spriteKind as ResourceGroup)
    ? node.spriteKind
    : 'generic') as ResourceGroup;
}

export function SelectedResourcePanel({
  graph,
  costs,
  selectedId,
  onSelectNode,
  onClose,
}: Props) {
  const node = graph.nodes.find((n) => n.id === selectedId);
  const line = costs.lines.find((l) => l.nodeId === selectedId);
  const meta = node ? GROUP_META[groupOf(node)] : null;
  const explain = node ? explainResource(node.type) : null;

  const icon = useMemo(() => {
    if (!node) return '';
    return tfSpriteDataUrl(node.spriteKind, node.cloud);
  }, [node]);

  if (!node || !meta || !explain) return null;

  return (
    <aside
      className="sb-selected-panel"
      role="dialog"
      aria-label="Selected resource"
      style={{ borderColor: `${meta.accent}55`, ['--accent' as string]: meta.accent }}
    >
      <div className="sb-selected-panel-head">
        <p className="sb-section-label">Selected</p>
        <button type="button" className="sb-icon-btn" aria-label="Clear selection" onClick={onClose}>
          <X size={16} />
        </button>
      </div>

      <div className="sb-selected-panel-body">
        <div className="sb-detail">
          <div className="sb-detail-top">
            <img src={icon} alt="" draggable={false} />
            <div className="sb-detail-titles">
              <h3>{explain.label}</h3>
              <p className="sb-detail-addr">{node.address}</p>
            </div>
            <div className="sb-detail-price">
              <strong>${(line?.monthlyUsd ?? 0).toFixed(2)}</strong>
              <span>/mo</span>
            </div>
          </div>

          <div className="sb-explain">
            <div>
              <p className="sb-explain-k">What it does</p>
              <p className="sb-explain-v">{explain.does}</p>
            </div>
            <div>
              <p className="sb-explain-k">Used for</p>
              <p className="sb-explain-v">{explain.usedFor}</p>
            </div>
          </div>

          <dl className="sb-detail-grid">
            <dt>Group</dt>
            <dd style={{ color: meta.accent }}>{meta.label}</dd>
            <dt>Type</dt>
            <dd>{node.type}</dd>
            <dt>Cloud</dt>
            <dd>{node.cloud}</dd>
            <dt>Module</dt>
            <dd>{moduleLabel(node.modulePath)}</dd>
            <dt>SKU</dt>
            <dd>{node.attrs.sku ?? '—'}</dd>
            <dt>Region</dt>
            <dd>{node.attrs.region ?? '—'}</dd>
            {line?.basis && (
              <>
                <dt>Basis</dt>
                <dd>{line.basis}</dd>
              </>
            )}
          </dl>

          {node.dependencies.length > 0 && (
            <div className="sb-deps-block">
              <p className="sb-section-label">Depends on</p>
              <ul className="sb-deps">
                {node.dependencies.map((d) => {
                  const depId = resolveDepId(graph, d);
                  return (
                    <li key={d}>
                      {depId ? (
                        <button type="button" className="sb-dep-link" onClick={() => onSelectNode(depId)}>
                          {d}
                        </button>
                      ) : (
                        d
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
