import { useEffect, useMemo, useRef, useState } from 'react';
import {
  createLiveSandbox,
  demoBuildings,
  demoUnits,
  type LiveSandboxHandle,
} from './createLiveSandbox';
import { liveSpriteDataUrl } from './liveSprites';
import { UNIT_LABELS, type LiveUnitKind, type LiveUnitPlacement } from './liveUnitKinds';

const ROSTER: LiveUnitKind[] = ['drone', 'cyber', 'firewall', 'swarm', 'agent', 'nano'];

export function LiveSandboxView() {
  const hostRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<LiveSandboxHandle | null>(null);
  const [selected, setSelected] = useState<LiveUnitPlacement | null>(null);
  const [error, setError] = useState<string | null>(null);

  const icons = useMemo(() => {
    const map: Partial<Record<LiveUnitKind, string>> = {};
    for (const k of ROSTER) map[k] = liveSpriteDataUrl(k);
    return map;
  }, []);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    let cancelled = false;

    void createLiveSandbox(host, demoUnits(), demoBuildings(), {
      onSelectUnit: (u) => {
        if (!cancelled) setSelected(u);
      },
    })
      .then((handle) => {
        if (cancelled) {
          handle.destroy();
          return;
        }
        engineRef.current = handle;
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to start sandbox');
      });

    return () => {
      cancelled = true;
      engineRef.current?.destroy();
      engineRef.current = null;
    };
  }, []);

  return (
    <div className="live-sandbox-wrap">
      <div ref={hostRef} className="live-sandbox-viewport" />
      {error && <p className="live-sandbox-error">{error}</p>}
      <div className="live-sandbox-hud">
        <div className="live-sandbox-resources">
          <span>Res 420</span>
          <span>Energy 18</span>
          <span>Stability 72</span>
          <span className="live-sandbox-timer">24:00</span>
        </div>
        <div className="live-sandbox-roster" aria-label="Unit roster">
          {ROSTER.map((kind) => (
            <div
              key={kind}
              className={
                selected?.kind === kind ? 'live-sandbox-card live-sandbox-card--active' : 'live-sandbox-card'
              }
            >
              <img src={icons[kind]} alt="" width={48} height={48} draggable={false} />
              <span>{UNIT_LABELS[kind]}</span>
            </div>
          ))}
        </div>
        {selected ? (
          <p className="live-sandbox-selection">
            {UNIT_LABELS[selected.kind]}
            <span className="live-sandbox-team"> · {selected.team}</span>
            <span> · HP {Math.round(selected.hp * 100)}%</span>
            <span className="live-sandbox-hint"> · click a land hex to move</span>
          </p>
        ) : (
          <p className="live-sandbox-selection live-sandbox-selection--muted">
            Select a unit, then click a land hex to move (max 5 hexes)
          </p>
        )}
      </div>
    </div>
  );
}
