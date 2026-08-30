import { useEffect, useRef } from 'react';
import type { CostReport, HexPlacement, InfraGraph } from '@stateboard/tf-cost';
import {
  createStateboardMap,
  type StateboardMapHandle,
} from './createStateboardMap';

type Props = {
  graph: InfraGraph;
  costs: CostReport | null;
  onSelect: (p: HexPlacement | null) => void;
};

export function StateboardMapView({ graph, costs, onSelect }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<StateboardMapHandle | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    let cancelled = false;

    void createStateboardMap(host, graph, costs, {
      onSelect: (p) => {
        if (!cancelled) onSelectRef.current(p);
      },
    }).then((handle) => {
      if (cancelled) {
        handle.destroy();
        return;
      }
      engineRef.current = handle;
    });

    return () => {
      cancelled = true;
      engineRef.current?.destroy();
      engineRef.current = null;
    };
  }, [graph, costs]);

  return (
    <div className="live-sandbox-wrap">
      <div ref={hostRef} className="live-sandbox-viewport" />
    </div>
  );
}
