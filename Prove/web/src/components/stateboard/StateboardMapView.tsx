import { useEffect, useRef } from 'react';
import type { HexPlacement, InfraGraph } from '@stateboard/tf-cost';
import type { TerraformVisualization } from '../../api';
import {
  createStateboardMap,
  type StateboardMapHandle,
} from './createStateboardMap';

type Props = {
  visualization: TerraformVisualization;
  graph: InfraGraph;
  selectedId: string | null;
  onSelect: (p: HexPlacement | null) => void;
};

export function StateboardMapView({ visualization, graph, selectedId, onSelect }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<StateboardMapHandle | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    let cancelled = false;

    void createStateboardMap(host, visualization, {
      onSelect: (p) => {
        if (!cancelled) onSelectRef.current(p);
      },
    }).then((handle) => {
      if (cancelled) {
        handle.destroy();
        return;
      }
      engineRef.current = handle;
      if (selectedId) handle.setSelectedId(selectedId, { focus: true, silent: true });
    });

    return () => {
      cancelled = true;
      engineRef.current?.destroy();
      engineRef.current = null;
    };
    // Recreate map when architecture changes — not on every selection.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visualization, graph]);

  useEffect(() => {
    engineRef.current?.setSelectedId(selectedId, { focus: true, silent: true });
  }, [selectedId]);

  return (
    <div className="live-sandbox-wrap">
      <div ref={hostRef} className="live-sandbox-viewport" />
    </div>
  );
}
