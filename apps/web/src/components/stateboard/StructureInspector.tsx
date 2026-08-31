import { ChevronDown, Search, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import type { CostReport, InfraGraph, InfraNode, SpriteKind } from '@stateboard/tf-cost';
import { explainResource } from './resourceExplain';
import { GROUP_META, GROUP_ORDER, type ResourceGroup } from './resourceGroups';
import { tfSpriteDataUrl } from './tfSprites';

type Props = {
  graph: InfraGraph;
  costs: CostReport;
  selectedId: string | null;
  sourceLabel: string;
  onSelectNode: (nodeId: string) => void;
  onClose: () => void;
};

function groupOf(node: InfraNode): ResourceGroup {
  return (GROUP_ORDER.includes(node.spriteKind as ResourceGroup)
    ? node.spriteKind
    : 'generic') as ResourceGroup;
}

export function StructureInspector({
  graph,
  costs,
  selectedId,
  sourceLabel,
  onSelectNode,
  onClose,
}: Props) {
  const [query, setQuery] = useState('');
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    for (const k of GROUP_ORDER) init[k] = true;
    return init;
  });

  const icons = useMemo(() => {
    const map: Partial<Record<SpriteKind, string>> = {};
    for (const n of graph.nodes) {
      if (!map[n.spriteKind]) map[n.spriteKind] = tfSpriteDataUrl(n.spriteKind, n.cloud);
    }
    return map;
  }, [graph.nodes]);

  const costById = useMemo(
    () => new Map(costs.lines.map((l) => [l.nodeId, l])),
    [costs.lines],
  );

  const byGroup = useMemo(() => {
    const map = new Map<ResourceGroup, InfraNode[]>();
    for (const n of graph.nodes) {
      const g = groupOf(n);
      const list = map.get(g) ?? [];
      list.push(n);
      map.set(g, list);
    }
    return map;
  }, [graph.nodes]);

  const groups = GROUP_ORDER.filter((k) => (byGroup.get(k)?.length ?? 0) > 0);
  const selectedNode = graph.nodes.find((n) => n.id === selectedId);

  const q = query.trim().toLowerCase();
  const filteredByGroup = useMemo(() => {
    const map = new Map<ResourceGroup, InfraNode[]>();
    for (const g of groups) {
      const nodes = [...(byGroup.get(g) ?? [])]
        .filter((n) => {
          if (!q) return true;
          const ex = explainResource(n.type);
          return (
            n.name.toLowerCase().includes(q) ||
            n.type.toLowerCase().includes(q) ||
            n.address.toLowerCase().includes(q) ||
            ex.label.toLowerCase().includes(q) ||
            ex.does.toLowerCase().includes(q)
          );
        })
        .sort((a, b) => a.address.localeCompare(b.address));
      if (nodes.length) map.set(g, nodes);
    }
    return map;
  }, [byGroup, groups, q]);

  const visibleGroups = groups.filter((g) => (filteredByGroup.get(g)?.length ?? 0) > 0);

  useEffect(() => {
    if (!selectedNode) return;
    const g = groupOf(selectedNode);
    setOpenGroups((s) => (s[g] ? s : { ...s, [g]: true }));
    requestAnimationFrame(() => {
      document.querySelector('.sb-resource--active')?.scrollIntoView({ block: 'nearest' });
    });
  }, [selectedNode]);

  useEffect(() => {
    if (!q) return;
    setOpenGroups((s) => {
      const next = { ...s };
      let changed = false;
      for (const g of GROUP_ORDER) {
        if ((filteredByGroup.get(g)?.length ?? 0) > 0 && !next[g]) {
          next[g] = true;
          changed = true;
        }
      }
      return changed ? next : s;
    });
  }, [q, filteredByGroup]);

  const focusGroup = (g: ResourceGroup) => {
    setOpenGroups((s) => ({ ...s, [g]: true }));
    requestAnimationFrame(() => {
      document.getElementById(`sb-group-${g}`)?.scrollIntoView({ block: 'nearest' });
    });
  };

  return (
    <aside className="sb-inspector" aria-label="Terraform structure" role="dialog">
      <div className="sb-inspector-head">
        <div className="sb-inspector-head-text">
          <h2>Structure</h2>
          <p className="sb-inspector-meta">
            {graph.nodes.length} resources · ${costs.totalMonthlyUsd.toFixed(0)}/mo
          </p>
          <p className="sb-inspector-source" title={sourceLabel}>
            {sourceLabel}
          </p>
        </div>
        <button
          type="button"
          className="sb-icon-btn"
          aria-label="Close structure"
          onClick={onClose}
        >
          <X size={16} />
        </button>
      </div>

      <div className="sb-inspector-toolbar">
        <label className="sb-search">
          <Search size={14} aria-hidden />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search resources…"
            aria-label="Search resources"
          />
        </label>
        <div className="sb-group-pills" role="tablist" aria-label="Destination groups">
          {groups.map((g) => {
            const meta = GROUP_META[g];
            const nodes = byGroup.get(g) ?? [];
            const usd = nodes.reduce((s, n) => s + (costById.get(n.id)?.monthlyUsd ?? 0), 0);
            const active = selectedNode ? groupOf(selectedNode) === g : false;
            return (
              <button
                key={g}
                type="button"
                role="tab"
                className={`sb-group-pill${active ? ' sb-group-pill--active' : ''}`}
                style={{ ['--pill' as string]: meta.accent }}
                onClick={() => focusGroup(g)}
                title={`${meta.label}: ${nodes.length} · $${usd.toFixed(0)}/mo`}
              >
                <span className="sb-group-pill-dot" />
                <span className="sb-group-pill-label">{meta.short}</span>
                <span className="sb-group-pill-cost">${usd.toFixed(0)}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="sb-inspector-body">
        <div className="sb-list-block">
          <p className="sb-section-label">
            Resources{q ? ` · ${[...filteredByGroup.values()].reduce((n, xs) => n + xs.length, 0)} matches` : ''}
          </p>
          {visibleGroups.length === 0 ? (
            <p className="sb-empty-hint">No resources match “{query}”.</p>
          ) : (
            <div className="sb-group-stack">
              {visibleGroups.map((g) => {
                const meta = GROUP_META[g];
                const nodes = filteredByGroup.get(g) ?? [];
                const open = openGroups[g] ?? true;
                const usd = nodes.reduce((s, n) => s + (costById.get(n.id)?.monthlyUsd ?? 0), 0);
                return (
                  <div
                    key={g}
                    id={`sb-group-${g}`}
                    className="sb-module"
                    style={{ borderColor: `${meta.accent}40` }}
                  >
                    <button
                      type="button"
                      className="sb-module-head"
                      aria-expanded={open}
                      onClick={() => setOpenGroups((s) => ({ ...s, [g]: !open }))}
                    >
                      <span className="sb-group-dot" style={{ background: meta.accent }} aria-hidden />
                      <span className="sb-module-name" style={{ color: meta.accent }}>
                        {meta.label}
                      </span>
                      <span className="sb-module-count">{nodes.length}</span>
                      <span className="sb-module-cost">${usd.toFixed(2)}</span>
                      <ChevronDown
                        size={14}
                        className={`sb-chevron${open ? ' sb-chevron--open' : ''}`}
                        aria-hidden
                      />
                    </button>
                    {open && (
                      <ul className="sb-resource-list">
                        {nodes.map((n) => {
                          const line = costById.get(n.id);
                          const ex = explainResource(n.type);
                          const active = n.id === selectedId;
                          return (
                            <li key={n.id}>
                              <button
                                type="button"
                                className={active ? 'sb-resource sb-resource--active' : 'sb-resource'}
                                style={active ? { borderColor: `${meta.accent}88` } : undefined}
                                onClick={() => onSelectNode(n.id)}
                              >
                                <img src={icons[n.spriteKind]} alt="" draggable={false} />
                                <span className="sb-resource-main">
                                  <span className="sb-resource-addr">{n.name}</span>
                                  <span className="sb-resource-label">{ex.label}</span>
                                  <span className="sb-resource-blurb">{ex.does}</span>
                                </span>
                                <span className="sb-resource-cost">
                                  ${(line?.monthlyUsd ?? 0).toFixed(0)}
                                </span>
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
