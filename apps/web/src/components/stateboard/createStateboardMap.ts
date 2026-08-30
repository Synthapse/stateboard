import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { Cloud, CostReport, HexPlacement, InfraGraph } from '@stateboard/tf-cost';
import { layoutResourcesToHex } from '@stateboard/tf-cost';
import { createSelectionRing, createTfResourceSprite } from './tfSprites';

const HEX_SIZE = 1.05;
const SQRT3 = Math.sqrt(3);

const CLOUD_TOP: Record<Cloud, number> = {
  aws: 0x8a5a30,
  azure: 0x3a6a7a,
  gcp: 0x3a7a68,
  other: 0x4a5560,
};

const CLOUD_SIDE: Record<Cloud, number> = {
  aws: 0x5a3a18,
  azure: 0x1e4a5c,
  gcp: 0x1e5a48,
  other: 0x2a3540,
};

export type StateboardMapHandle = {
  setSelectedId: (id: string | null) => void;
  destroy: () => void;
};

export type StateboardMapCallbacks = {
  onSelect: (placement: HexPlacement | null) => void;
};

function axialToWorld(q: number, r: number): THREE.Vector3 {
  return new THREE.Vector3(HEX_SIZE * SQRT3 * (q + r / 2), 0, HEX_SIZE * 1.5 * r);
}

function makeHex(size: number, height: number, top: number, side: number): THREE.Group {
  const g = new THREE.Group();
  const shape = new THREE.Shape();
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 180) * (60 * i - 30);
    const x = size * Math.cos(a);
    const y = size * Math.sin(a);
    if (i === 0) shape.moveTo(x, y);
    else shape.lineTo(x, y);
  }
  shape.closePath();
  const sideGeo = new THREE.ExtrudeGeometry(shape, { depth: height, bevelEnabled: false });
  sideGeo.rotateX(-Math.PI / 2);
  g.add(
    new THREE.Mesh(
      sideGeo,
      new THREE.MeshStandardMaterial({ color: side, flatShading: true, roughness: 0.85 }),
    ),
  );
  const topShape = shape.clone();
  const topGeo = new THREE.ShapeGeometry(topShape);
  topGeo.rotateX(-Math.PI / 2);
  const topMesh = new THREE.Mesh(
    topGeo,
    new THREE.MeshStandardMaterial({ color: top, flatShading: true, roughness: 0.7 }),
  );
  topMesh.position.y = height + 0.002;
  topMesh.name = 'hex-top';
  g.add(topMesh);
  return g;
}

function waitForHost(host: HTMLElement): Promise<void> {
  return new Promise((resolve) => {
    if (host.clientWidth >= 2 && host.clientHeight >= 2) {
      resolve();
      return;
    }
    const obs = new ResizeObserver(() => {
      if (host.clientWidth >= 2) {
        obs.disconnect();
        resolve();
      }
    });
    obs.observe(host);
  });
}

export async function createStateboardMap(
  host: HTMLElement,
  graph: InfraGraph,
  costs: CostReport | null,
  callbacks: StateboardMapCallbacks,
): Promise<StateboardMapHandle> {
  await waitForHost(host);

  const placements = layoutResourcesToHex(graph, costs);
  const maxCost = Math.max(1, ...placements.map((p) => p.monthlyUsd));

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x071828);
  scene.fog = new THREE.Fog(0x071828, 28, 55);

  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 200);
  camera.position.set(12, 16, 14);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setClearColor(0x071828, 1);
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(host.clientWidth, host.clientHeight, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.domElement.classList.add('live-sandbox-canvas');
  host.appendChild(renderer.domElement);

  scene.add(new THREE.HemisphereLight(0xb8d4f0, 0x1a3030, 0.7));
  const sun = new THREE.DirectionalLight(0xfff2dd, 1.3);
  sun.position.set(8, 16, 6);
  scene.add(sun);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.target.set(0, 0.2, 0);
  controls.minDistance = 8;
  controls.maxDistance = 40;

  const board = new THREE.Group();
  scene.add(board);

  // Water backdrop hexes
  const radius = 8;
  for (let q = -radius; q <= radius; q++) {
    for (let r = -radius; r <= radius; r++) {
      if (Math.abs(q + r) > radius) continue;
      const g = makeHex(HEX_SIZE * 0.96, 0.06, 0x1a3a52, 0x102838);
      g.position.copy(axialToWorld(q, r));
      board.add(g);
    }
  }

  const tokens = new THREE.Group();
  scene.add(tokens);
  const pickables: THREE.Object3D[] = [];
  const byId = new Map<string, { placement: HexPlacement; mesh: THREE.Group }>();

  for (const p of placements) {
    const height = 0.16 + Math.min(0.55, (p.monthlyUsd / maxCost) * 0.5);
    const tile = makeHex(HEX_SIZE * 0.96, height, CLOUD_TOP[p.cloud], CLOUD_SIDE[p.cloud]);
    tile.position.copy(axialToWorld(p.q, p.r));
    board.add(tile);

    const mesh = createTfResourceSprite(p.spriteKind, p.cloud, p.monthlyUsd, maxCost);
    mesh.position.copy(axialToWorld(p.q, p.r));
    mesh.position.y = height + 0.02;
    mesh.userData.nodeId = p.nodeId;
    tokens.add(mesh);
    pickables.push(mesh);
    byId.set(p.nodeId, { placement: p, mesh });
  }

  const ring = createSelectionRing();
  ring.visible = false;
  scene.add(ring);

  const setSelectedId = (id: string | null) => {
    if (!id) {
      ring.visible = false;
      callbacks.onSelect(null);
      return;
    }
    const entry = byId.get(id);
    if (!entry) return;
    ring.visible = true;
    ring.position.set(entry.mesh.position.x, entry.mesh.position.y, entry.mesh.position.z);
    callbacks.onSelect(entry.placement);
  };

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  let down = new THREE.Vector2();
  let dragged = false;

  const setPtr = (e: PointerEvent) => {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  };

  const onDown = (e: PointerEvent) => {
    if (e.button !== 0) return;
    setPtr(e);
    down.set(e.clientX, e.clientY);
    dragged = false;
  };
  const onMove = (e: PointerEvent) => {
    if (e.buttons === 1 && (Math.abs(e.clientX - down.x) > 4 || Math.abs(e.clientY - down.y) > 4)) {
      dragged = true;
    }
  };
  const onUp = (e: PointerEvent) => {
    if (e.button !== 0 || dragged) return;
    setPtr(e);
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(pickables, true);
    if (!hits.length) {
      setSelectedId(null);
      return;
    }
    let o: THREE.Object3D | null = hits[0].object;
    while (o && o.userData.nodeId == null) o = o.parent;
    if (o?.userData.nodeId) setSelectedId(o.userData.nodeId as string);
  };

  renderer.domElement.addEventListener('pointerdown', onDown);
  renderer.domElement.addEventListener('pointermove', onMove);
  renderer.domElement.addEventListener('pointerup', onUp);

  let raf = 0;
  const tick = () => {
    raf = requestAnimationFrame(tick);
    controls.update();
    const w = host.clientWidth;
    const h = host.clientHeight;
    if (w > 0 && h > 0) {
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h, false);
    }
    renderer.render(scene, camera);
  };
  tick();

  if (placements[0]) setSelectedId(placements[0].nodeId);

  return {
    setSelectedId,
    destroy: () => {
      cancelAnimationFrame(raf);
      renderer.domElement.removeEventListener('pointerdown', onDown);
      renderer.domElement.removeEventListener('pointermove', onMove);
      renderer.domElement.removeEventListener('pointerup', onUp);
      controls.dispose();
      renderer.dispose();
      if (renderer.domElement.parentElement === host) host.removeChild(renderer.domElement);
    },
  };
}
