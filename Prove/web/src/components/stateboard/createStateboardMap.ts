import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { HexPlacement, SpriteKind } from '@stateboard/tf-cost';
import type { DependencyEdge, TerraformVisualization } from '../../api';
import { GROUP_META, GROUP_ORDER, type ResourceGroup } from './resourceGroups';
import { createSelectionRing, createTfResourceSprite } from './tfSprites';

const HEX_SIZE = 1.05;
const SQRT3 = Math.sqrt(3);

export type StateboardMapHandle = {
  setSelectedId: (id: string | null, opts?: { focus?: boolean; silent?: boolean }) => void;
  destroy: () => void;
};

export type StateboardMapCallbacks = {
  onSelect: (placement: HexPlacement | null) => void;
};

function axialToWorld(q: number, r: number): THREE.Vector3 {
  return new THREE.Vector3(HEX_SIZE * SQRT3 * (q + r / 2), 0, HEX_SIZE * 1.5 * r);
}

function makeHex(size: number, height: number, top: number, side: number, opacity = 1): THREE.Group {
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
      new THREE.MeshStandardMaterial({
        color: side,
        flatShading: true,
        roughness: 0.85,
        transparent: opacity < 1,
        opacity,
      }),
    ),
  );
  const topGeo = new THREE.ShapeGeometry(shape.clone());
  topGeo.rotateX(-Math.PI / 2);
  const topMesh = new THREE.Mesh(
    topGeo,
    new THREE.MeshStandardMaterial({
      color: top,
      flatShading: true,
      roughness: 0.7,
      transparent: opacity < 1,
      opacity,
    }),
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

function groupLabelSprite(text: string, accentHex: string): THREE.Sprite {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 64;
  const ctx = canvas.getContext('2d')!;
  ctx.clearRect(0, 0, 256, 64);
  ctx.fillStyle = 'rgba(5,20,36,0.82)';
  ctx.beginPath();
  ctx.roundRect(24, 16, 208, 32, 8);
  ctx.fill();
  ctx.strokeStyle = accentHex;
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = accentHex;
  ctx.font = '600 20px ui-sans-serif, system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, 128, 32, 190);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  const spr = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }),
  );
  spr.scale.set(1.8, 0.45, 1);
  spr.center.set(0.5, 0.5);
  return spr;
}

function drawEdges(
  scene: THREE.Scene,
  placements: HexPlacement[],
  edges: DependencyEdge[],
  heightById: Map<string, number>,
) {
  const byId = new Map(placements.map((p) => [p.nodeId, p]));
  const group = new THREE.Group();
  group.name = 'dep-edges';
  for (const e of edges) {
    const a = byId.get(e.from);
    const b = byId.get(e.to);
    if (!a || !b) continue;
    const from = axialToWorld(a.q, a.r);
    const to = axialToWorld(b.q, b.r);
    from.y = (heightById.get(a.nodeId) ?? 0.2) + 0.28;
    to.y = (heightById.get(b.nodeId) ?? 0.2) + 0.28;
    const mid = from.clone().lerp(to, 0.5);
    mid.y += 0.35;
    const curve = new THREE.QuadraticBezierCurve3(from, mid, to);
    const geo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(12));
    const line = new THREE.Line(
      geo,
      new THREE.LineDashedMaterial({
        color: 0x5a9bb5,
        dashSize: 0.12,
        gapSize: 0.1,
        transparent: true,
        opacity: 0.45,
      }),
    );
    line.computeLineDistances();
    group.add(line);
  }
  scene.add(group);
}

/** Subtle destination labels — no overlapping pads (tiles already carry group color). */
function drawResourceGroups(scene: THREE.Scene, placements: HexPlacement[]) {
  const byKind = new Map<SpriteKind, HexPlacement[]>();
  for (const p of placements) {
    const list = byKind.get(p.spriteKind) ?? [];
    list.push(p);
    byKind.set(p.spriteKind, list);
  }

  const root = new THREE.Group();
  root.name = 'resource-groups';

  const kinds = [
    ...GROUP_ORDER.filter((k) => byKind.has(k)),
    ...[...byKind.keys()].filter((k) => !GROUP_ORDER.includes(k as ResourceGroup)),
  ];

  for (const kind of kinds) {
    const items = byKind.get(kind)!;
    const meta = GROUP_META[kind as ResourceGroup] ?? GROUP_META.generic;
    const pts = items.map((p) => axialToWorld(p.q, p.r));
    if (!pts.length) continue;

    const cx = pts.reduce((s, p) => s + p.x, 0) / pts.length;
    const cz = pts.reduce((s, p) => s + p.z, 0) / pts.length;
    let maxR = HEX_SIZE;
    for (const p of pts) {
      maxR = Math.max(maxR, Math.hypot(p.x - cx, p.z - cz) + HEX_SIZE * 0.7);
    }

    const accentNum = Number.parseInt(meta.accent.slice(1), 16);
    const ringPts: THREE.Vector3[] = [];
    for (let i = 0; i <= 6; i++) {
      const a = (Math.PI / 180) * (60 * i - 30);
      ringPts.push(new THREE.Vector3(cx + maxR * Math.cos(a), 0.03, cz + maxR * Math.sin(a)));
    }
    root.add(
      new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(ringPts),
        new THREE.LineBasicMaterial({ color: accentNum, transparent: true, opacity: 0.28 }),
      ),
    );

    const label = groupLabelSprite(meta.label, meta.accent);
    label.position.set(cx, 0.06, cz - maxR - 0.35);
    root.add(label);
  }

  scene.add(root);
}

export async function createStateboardMap(
  host: HTMLElement,
  visualization: TerraformVisualization,
  callbacks: StateboardMapCallbacks,
): Promise<StateboardMapHandle> {
  await waitForHost(host);

  const placements = visualization.placements;
  const maxCost = Math.max(1, visualization.maxMonthlyUsd, ...placements.map((p) => p.monthlyUsd));

  const worlds = placements.map((p) => axialToWorld(p.q, p.r));
  let minX = 0;
  let maxX = 0;
  let minZ = 0;
  let maxZ = 0;
  let boardRadius = 6;
  if (worlds.length) {
    minX = Math.min(...worlds.map((w) => w.x));
    maxX = Math.max(...worlds.map((w) => w.x));
    minZ = Math.min(...worlds.map((w) => w.z));
    maxZ = Math.max(...worlds.map((w) => w.z));
    for (const p of placements) {
      boardRadius = Math.max(boardRadius, Math.abs(p.q), Math.abs(p.r), Math.abs(p.q + p.r));
    }
    boardRadius += 2;
  }
  const centerX = (minX + maxX) / 2 + 1.6; // bias right so Structure panel doesn't cover the estate
  const centerZ = (minZ + maxZ) / 2;
  const span = Math.max(maxX - minX, maxZ - minZ, 4);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x061320);
  scene.fog = new THREE.Fog(0x061320, Math.max(22, span * 2.2), Math.max(48, span * 5));

  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 200);
  const camDist = Math.max(11, span * 1.35 + 4);
  camera.position.set(centerX + camDist * 0.62, camDist * 0.78, centerZ + camDist * 0.62);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setClearColor(0x061320, 1);
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(host.clientWidth, host.clientHeight, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.08;
  renderer.domElement.classList.add('live-sandbox-canvas');
  host.appendChild(renderer.domElement);

  scene.add(new THREE.HemisphereLight(0xb8d4f0, 0x0e2430, 0.6));
  const sun = new THREE.DirectionalLight(0xfff2dd, 1.1);
  sun.position.set(centerX + 10, 18, centerZ + 8);
  scene.add(sun);
  const fill = new THREE.DirectionalLight(0x4cd7f6, 0.2);
  fill.position.set(centerX - 8, 6, centerZ - 4);
  scene.add(fill);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.target.set(centerX, 0.25, centerZ);
  controls.minDistance = 5;
  controls.maxDistance = Math.max(36, span * 4);
  controls.maxPolarAngle = Math.PI * 0.46;

  const board = new THREE.Group();
  scene.add(board);

  const radius = boardRadius;
  for (let q = -radius; q <= radius; q++) {
    for (let r = -radius; r <= radius; r++) {
      if (Math.abs(q + r) > radius) continue;
      const g = makeHex(HEX_SIZE * 0.96, 0.05, 0x143248, 0x0c2234, 0.85);
      g.position.copy(axialToWorld(q, r));
      board.add(g);
    }
  }

  drawResourceGroups(scene, placements);

  const tokens = new THREE.Group();
  scene.add(tokens);
  const pickables: THREE.Object3D[] = [];
  const byId = new Map<string, { placement: HexPlacement; mesh: THREE.Group }>();
  const heightById = new Map<string, number>();

  for (const p of placements) {
    const height = 0.14 + Math.min(0.35, (p.monthlyUsd / maxCost) * 0.32);
    heightById.set(p.nodeId, height);
    const meta = GROUP_META[p.spriteKind] ?? GROUP_META.generic;
    const tile = makeHex(HEX_SIZE * 0.9, height, meta.hexTop, meta.hexSide);
    tile.position.copy(axialToWorld(p.q, p.r));
    board.add(tile);

    const mesh = createTfResourceSprite(p.spriteKind, p.cloud, p.monthlyUsd, maxCost);
    mesh.position.copy(axialToWorld(p.q, p.r));
    mesh.position.y = height + 0.01;
    mesh.userData.nodeId = p.nodeId;
    tokens.add(mesh);
    pickables.push(mesh);
    byId.set(p.nodeId, { placement: p, mesh });
  }

  drawEdges(scene, placements, visualization.edges, heightById);

  const ring = createSelectionRing();
  ring.visible = false;
  scene.add(ring);

  const focusOn = (x: number, z: number) => {
    const prev = controls.target.clone();
    const next = new THREE.Vector3(x, 0.35, z);
    const delta = next.clone().sub(prev);
    controls.target.copy(next);
    camera.position.add(delta);
    controls.update();
  };

  const setSelectedId = (id: string | null, opts?: { focus?: boolean; silent?: boolean }) => {
    if (!id) {
      ring.visible = false;
      if (!opts?.silent) callbacks.onSelect(null);
      return;
    }
    const entry = byId.get(id);
    if (!entry) return;
    ring.visible = true;
    ring.position.set(entry.mesh.position.x, entry.mesh.position.y, entry.mesh.position.z);
    if (opts?.focus) {
      focusOn(entry.mesh.position.x, entry.mesh.position.z);
    }
    if (!opts?.silent) callbacks.onSelect(entry.placement);
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
