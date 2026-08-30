import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import {
  createBuildingSprite,
  createPathGhost,
  createSelectionRing,
  createUnitSprite,
  setSpriteHp,
} from './liveSprites';
import type {
  LiveBuildingPlacement,
  LiveUnitKind,
  LiveUnitPlacement,
} from './liveUnitKinds';
import { UNIT_LABELS } from './liveUnitKinds';

const HEX_SIZE = 1.05;
const SQRT3 = Math.sqrt(3);
const MOVE_SPEED = 5.5; // world units / second

export type LiveSandboxHandle = {
  setSelectedId: (id: string | null) => void;
  destroy: () => void;
};

export type LiveSandboxCallbacks = {
  onSelectUnit: (unit: LiveUnitPlacement | null) => void;
};

type Biome = 'grass' | 'hills' | 'rock' | 'water';

type HexTile = {
  q: number;
  r: number;
  biome: Biome;
  height: number;
  mesh: THREE.Mesh;
  topMat: THREE.MeshStandardMaterial;
  baseColor: THREE.Color;
  hoverColor: THREE.Color;
};

function axialToWorld(q: number, r: number): THREE.Vector3 {
  const x = HEX_SIZE * SQRT3 * (q + r / 2);
  const z = HEX_SIZE * 1.5 * r;
  return new THREE.Vector3(x, 0, z);
}

function axialDist(aq: number, ar: number, bq: number, br: number): number {
  return (Math.abs(aq - bq) + Math.abs(ar - br) + Math.abs(aq + ar - bq - br)) / 2;
}

function biomeAt(q: number, r: number): Biome {
  const dist = Math.max(Math.abs(q), Math.abs(r), Math.abs(q + r));
  if (dist >= 5) return 'water';
  const n = Math.abs((q * 17 + r * 31) % 11);
  if (n <= 1) return 'rock';
  if (n <= 3) return 'hills';
  if (n === 4) return 'water';
  return 'grass';
}

const BIOME_STYLE: Record<
  Biome,
  { top: number; side: number; height: number; hover: number; walkable: boolean }
> = {
  grass: { top: 0x5c8f5a, side: 0x3a5c3c, height: 0.18, hover: 0x7cb87a, walkable: true },
  hills: { top: 0x7a8f5c, side: 0x4a5a38, height: 0.32, hover: 0x9ab070, walkable: true },
  rock: { top: 0x8b949e, side: 0x555e68, height: 0.48, hover: 0xa8b2bc, walkable: true },
  water: { top: 0x1e5a72, side: 0x123848, height: 0.07, hover: 0x2a7a94, walkable: false },
};

export function demoUnits(): LiveUnitPlacement[] {
  return [
    { id: 'u1', kind: 'pioneer', team: 'orange', q: -3, r: 1, hp: 1 },
    { id: 'u2', kind: 'drone', team: 'orange', q: -1, r: -1, hp: 0.9 },
    { id: 'u3', kind: 'cyber', team: 'orange', q: -2, r: 1, hp: 0.75 },
    { id: 'u4', kind: 'firewall', team: 'orange', q: -3, r: 0, hp: 1 },
    { id: 'u5', kind: 'battery', team: 'orange', q: -1, r: 2, hp: 0.8 },
    { id: 'u6', kind: 'swarm', team: 'steel', q: 3, r: 0, hp: 0.85, stack: 5 },
    { id: 'u7', kind: 'agent', team: 'steel', q: 4, r: -1, hp: 1 },
    { id: 'u8', kind: 'bio', team: 'steel', q: 3, r: 1, hp: 0.55 },
    { id: 'u9', kind: 'nano', team: 'steel', q: 2, r: 2, hp: 0.7 },
    { id: 'u10', kind: 'drone', team: 'steel', q: 2, r: -1, hp: 1 },
    { id: 'u11', kind: 'cyber', team: 'steel', q: 1, r: -2, hp: 0.6 },
  ];
}

export function demoBuildings(): LiveBuildingPlacement[] {
  return [
    { id: 'b1', kind: 'capital', team: 'orange', q: -4, r: 0 },
    { id: 'b2', kind: 'outpost', team: 'orange', q: -1, r: 0 },
    { id: 'b3', kind: 'lab', team: 'orange', q: -3, r: 2 },
    { id: 'b4', kind: 'capital', team: 'steel', q: 4, r: 0 },
    { id: 'b5', kind: 'outpost', team: 'steel', q: 2, r: 0 },
  ];
}

function waitForHostSize(host: HTMLElement): Promise<void> {
  return new Promise((resolve) => {
    const ready = () => host.clientWidth >= 2 && host.clientHeight >= 2;
    if (ready()) {
      resolve();
      return;
    }
    const observer = new ResizeObserver(() => {
      if (ready()) {
        observer.disconnect();
        resolve();
      }
    });
    observer.observe(host);
  });
}

/** Prism with separate top face (lighter) for a clearer board read. */
function makeHexTile(size: number, height: number, topColor: number, sideColor: number): THREE.Group {
  const g = new THREE.Group();
  const shape = new THREE.Shape();
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 180) * (60 * i - 30);
    const x = size * Math.cos(angle);
    const y = size * Math.sin(angle);
    if (i === 0) shape.moveTo(x, y);
    else shape.lineTo(x, y);
  }
  shape.closePath();

  const sideGeo = new THREE.ExtrudeGeometry(shape, { depth: height, bevelEnabled: false });
  sideGeo.rotateX(-Math.PI / 2);
  const sideMat = new THREE.MeshStandardMaterial({
    color: sideColor,
    roughness: 0.88,
    metalness: 0.04,
    flatShading: true,
  });
  const side = new THREE.Mesh(sideGeo, sideMat);
  g.add(side);

  const topShape = new THREE.Shape();
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 180) * (60 * i - 30);
    const x = size * 0.98 * Math.cos(angle);
    const y = size * 0.98 * Math.sin(angle);
    if (i === 0) topShape.moveTo(x, y);
    else topShape.lineTo(x, y);
  }
  topShape.closePath();
  const topGeo = new THREE.ShapeGeometry(topShape);
  topGeo.rotateX(-Math.PI / 2);
  const topMat = new THREE.MeshStandardMaterial({
    color: topColor,
    roughness: 0.72,
    metalness: 0.06,
    flatShading: true,
  });
  const top = new THREE.Mesh(topGeo, topMat);
  top.position.y = height + 0.002;
  top.name = 'hex-top';
  g.add(top);

  // Inner rim highlight
  const rimPts = Array.from({ length: 7 }, (_, i) => {
    const angle = (Math.PI / 180) * (60 * i - 30);
    return new THREE.Vector3(
      size * 0.97 * Math.cos(angle),
      height + 0.01,
      size * 0.97 * Math.sin(angle),
    );
  });
  g.add(
    new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(rimPts),
      new THREE.LineBasicMaterial({ color: 0x0a1520, transparent: true, opacity: 0.5 }),
    ),
  );

  return g;
}

function addPine(parent: THREE.Object3D, x: number, y: number, z: number, s = 1) {
  const trunk = new THREE.Mesh(
    new THREE.CylinderGeometry(0.03 * s, 0.04 * s, 0.18 * s, 5),
    new THREE.MeshStandardMaterial({ color: 0x4a3728, flatShading: true }),
  );
  trunk.position.set(x, y + 0.09 * s, z);
  const canopy = new THREE.Mesh(
    new THREE.ConeGeometry(0.14 * s, 0.35 * s, 6),
    new THREE.MeshStandardMaterial({ color: 0x2f5a38, flatShading: true }),
  );
  canopy.position.set(x, y + 0.32 * s, z);
  parent.add(trunk, canopy);
}

function addPeak(parent: THREE.Object3D, x: number, y: number, z: number, s = 1) {
  const peak = new THREE.Mesh(
    new THREE.ConeGeometry(0.28 * s, 0.55 * s, 5),
    new THREE.MeshStandardMaterial({ color: 0x9aa3ad, flatShading: true, roughness: 0.7 }),
  );
  peak.position.set(x, y + 0.28 * s, z);
  const snow = new THREE.Mesh(
    new THREE.ConeGeometry(0.12 * s, 0.18 * s, 5),
    new THREE.MeshStandardMaterial({ color: 0xe8eef4, flatShading: true }),
  );
  snow.position.set(x, y + 0.55 * s, z);
  parent.add(peak, snow);
}

type MoveAnim = {
  id: string;
  from: THREE.Vector3;
  to: THREE.Vector3;
  t: number;
  duration: number;
  toQ: number;
  toR: number;
};

export async function createLiveSandbox(
  host: HTMLElement,
  units: LiveUnitPlacement[],
  buildings: LiveBuildingPlacement[],
  callbacks: LiveSandboxCallbacks,
): Promise<LiveSandboxHandle> {
  await waitForHostSize(host);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x071828);
  scene.fog = new THREE.Fog(0x071828, 24, 44);

  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 200);
  camera.position.set(10, 14, 14);

  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, alpha: false });
  renderer.setClearColor(0x071828, 1);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(host.clientWidth, host.clientHeight, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.12;
  renderer.domElement.classList.add('live-sandbox-canvas');
  renderer.domElement.setAttribute('role', 'img');
  renderer.domElement.setAttribute('aria-label', 'Live RTS visual sandbox');
  host.appendChild(renderer.domElement);

  scene.add(new THREE.HemisphereLight(0xb8d4f0, 0x1a3030, 0.7));
  const sun = new THREE.DirectionalLight(0xfff2dd, 1.4);
  sun.position.set(8, 16, 6);
  scene.add(sun);
  scene.add(new THREE.DirectionalLight(0x4cd7f6, 0.22).translateX(-8).translateY(6).translateZ(-4));

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.maxPolarAngle = Math.PI / 2.25;
  controls.minDistance = 10;
  controls.maxDistance = 32;
  controls.target.set(0, 0.2, 0);

  const board = new THREE.Group();
  scene.add(board);
  const hexByKey = new Map<string, HexTile>();
  const hexPickables: THREE.Object3D[] = [];

  const radius = 6;
  for (let q = -radius; q <= radius; q++) {
    for (let r = -radius; r <= radius; r++) {
      if (Math.abs(q + r) > radius) continue;
      const biome = biomeAt(q, r);
      const style = BIOME_STYLE[biome];
      const tileGroup = makeHexTile(HEX_SIZE * 0.96, style.height, style.top, style.side);
      const pos = axialToWorld(q, r);
      tileGroup.position.copy(pos);
      board.add(tileGroup);

      const top = tileGroup.getObjectByName('hex-top') as THREE.Mesh;
      top.userData.hexKey = `${q},${r}`;
      hexPickables.push(top);

      if (biome === 'water') {
        (top.material as THREE.MeshStandardMaterial).transparent = true;
        (top.material as THREE.MeshStandardMaterial).opacity = 0.82;
        (top.material as THREE.MeshStandardMaterial).metalness = 0.35;
        (top.material as THREE.MeshStandardMaterial).roughness = 0.28;
      }

      const tile: HexTile = {
        q,
        r,
        biome,
        height: style.height,
        mesh: top,
        topMat: top.material as THREE.MeshStandardMaterial,
        baseColor: new THREE.Color(style.top),
        hoverColor: new THREE.Color(style.hover),
      };
      hexByKey.set(`${q},${r}`, tile);

      if (biome === 'grass' && (q + r * 3) % 5 === 0) {
        addPine(tileGroup, 0.15, style.height, -0.1, 0.85);
      }
      if (biome === 'rock') {
        addPeak(tileGroup, 0, style.height, 0, 0.7 + ((q + r) % 3) * 0.1);
      }
    }
  }

  const tokens = new THREE.Group();
  scene.add(tokens);
  const unitPickables: THREE.Object3D[] = [];
  const unitById = new Map<string, LiveUnitPlacement>();
  const meshById = new Map<string, THREE.Group>();
  const occupied = new Map<string, string>(); // hexKey -> unitId

  const surfaceY = (q: number, r: number) => (hexByKey.get(`${q},${r}`)?.height ?? 0.16) + 0.02;

  for (const b of buildings) {
    const mesh = createBuildingSprite(b.kind);
    mesh.position.copy(axialToWorld(b.q, b.r));
    mesh.position.y = surfaceY(b.q, b.r);
    tokens.add(mesh);
  }

  for (const u of units) {
    unitById.set(u.id, u);
    occupied.set(`${u.q},${u.r}`, u.id);
    const mesh = createUnitSprite(u.kind, u.hp);
    mesh.position.copy(axialToWorld(u.q, u.r));
    mesh.position.y = surfaceY(u.q, u.r);
    mesh.userData.unitId = u.id;
    mesh.userData.baseY = mesh.position.y;
    setSpriteHp(mesh, u.hp);
    tokens.add(mesh);
    meshById.set(u.id, mesh);
    unitPickables.push(mesh);
  }

  const selectionRing = createSelectionRing();
  selectionRing.visible = false;
  scene.add(selectionRing);

  let pathLine: THREE.Line | null = null;
  let selectedId: string | null = null;
  let hoveredHex: HexTile | null = null;
  let moveAnim: MoveAnim | null = null;
  let pointerDown = new THREE.Vector2();
  let dragMoved = false;

  const clearPath = () => {
    if (!pathLine) return;
    scene.remove(pathLine);
    pathLine.geometry.dispose();
    (pathLine.material as THREE.Material).dispose();
    pathLine = null;
  };

  const showPath = (from: THREE.Vector3, to: THREE.Vector3) => {
    clearPath();
    pathLine = createPathGhost(from, to);
    scene.add(pathLine);
  };

  const setHexHover = (tile: HexTile | null) => {
    if (hoveredHex && hoveredHex !== tile) {
      hoveredHex.topMat.color.copy(hoveredHex.baseColor);
      hoveredHex.topMat.emissive.setHex(0x000000);
      hoveredHex.topMat.emissiveIntensity = 0;
    }
    hoveredHex = tile;
    if (tile && BIOME_STYLE[tile.biome].walkable) {
      tile.topMat.color.copy(tile.hoverColor);
      tile.topMat.emissive.setHex(0x4cd7f6);
      tile.topMat.emissiveIntensity = 0.12;
    }
  };

  const refreshSelectionVisual = () => {
    if (!selectedId) {
      selectionRing.visible = false;
      clearPath();
      callbacks.onSelectUnit(null);
      return;
    }
    const unit = unitById.get(selectedId);
    const mesh = meshById.get(selectedId);
    if (!unit || !mesh) return;
    selectionRing.visible = true;
    selectionRing.position.set(mesh.position.x, surfaceY(unit.q, unit.r), mesh.position.z);
    callbacks.onSelectUnit({ ...unit });
  };

  const setSelectedId = (id: string | null) => {
    selectedId = id;
    refreshSelectionVisual();
  };

  const unitAt = (q: number, r: number) => {
    const id = occupied.get(`${q},${r}`);
    return id ? unitById.get(id) ?? null : null;
  };

  const canMoveTo = (unit: LiveUnitPlacement, q: number, r: number) => {
    const tile = hexByKey.get(`${q},${r}`);
    if (!tile || !BIOME_STYLE[tile.biome].walkable) return false;
    if (unit.q === q && unit.r === r) return false;
    const blocker = unitAt(q, r);
    if (blocker && blocker.id !== unit.id) return false;
    // Soft range for sandbox feel
    if (axialDist(unit.q, unit.r, q, r) > 5) return false;
    return true;
  };

  const startMove = (unit: LiveUnitPlacement, q: number, r: number) => {
    if (moveAnim) return;
    const mesh = meshById.get(unit.id);
    if (!mesh || !canMoveTo(unit, q, r)) return;

    const from = mesh.position.clone();
    const to = axialToWorld(q, r);
    to.y = surfaceY(q, r);
    const dist = from.distanceTo(to);
    occupied.delete(`${unit.q},${unit.r}`);
    occupied.set(`${q},${r}`, unit.id);
    unit.q = q;
    unit.r = r;

    moveAnim = {
      id: unit.id,
      from,
      to,
      t: 0,
      duration: Math.max(0.25, dist / MOVE_SPEED),
      toQ: q,
      toR: r,
    };
    showPath(from, to);
    refreshSelectionVisual();
  };

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  const setPointer = (event: PointerEvent) => {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  };

  const pickUnit = (): string | null => {
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(unitPickables, true);
    if (hits.length === 0) return null;
    let obj: THREE.Object3D | null = hits[0].object;
    while (obj && obj.userData.unitId == null) obj = obj.parent;
    return (obj?.userData.unitId as string) ?? null;
  };

  const pickHex = (): HexTile | null => {
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(hexPickables, false);
    if (hits.length === 0) return null;
    const key = hits[0].object.userData.hexKey as string | undefined;
    return key ? hexByKey.get(key) ?? null : null;
  };

  const onPointerDown = (event: PointerEvent) => {
    if (event.button !== 0) return;
    setPointer(event);
    pointerDown.set(event.clientX, event.clientY);
    dragMoved = false;
  };

  const onPointerMove = (event: PointerEvent) => {
    setPointer(event);
    if (
      event.buttons === 1 &&
      (Math.abs(event.clientX - pointerDown.x) > 4 || Math.abs(event.clientY - pointerDown.y) > 4)
    ) {
      dragMoved = true;
    }

    const hex = pickHex();
    setHexHover(hex && BIOME_STYLE[hex.biome].walkable ? hex : null);

    if (selectedId && !moveAnim) {
      const unit = unitById.get(selectedId);
      const mesh = meshById.get(selectedId);
      if (unit && mesh && hex && canMoveTo(unit, hex.q, hex.r)) {
        const to = axialToWorld(hex.q, hex.r);
        to.y = surfaceY(hex.q, hex.r);
        showPath(mesh.position.clone(), to);
      } else if (unit && mesh) {
        clearPath();
        selectionRing.position.set(mesh.position.x, surfaceY(unit.q, unit.r), mesh.position.z);
      }
    }
  };

  const onPointerUp = (event: PointerEvent) => {
    if (event.button !== 0 || dragMoved) return;
    setPointer(event);

    const unitId = pickUnit();
    if (unitId) {
      setSelectedId(unitId === selectedId ? selectedId : unitId);
      return;
    }

    const hex = pickHex();
    if (selectedId && hex) {
      const unit = unitById.get(selectedId);
      if (unit && canMoveTo(unit, hex.q, hex.r)) {
        startMove(unit, hex.q, hex.r);
        return;
      }
    }

    setSelectedId(null);
  };

  renderer.domElement.addEventListener('pointerdown', onPointerDown);
  renderer.domElement.addEventListener('pointermove', onPointerMove);
  renderer.domElement.addEventListener('pointerup', onPointerUp);

  let frame = 0;
  let raf = 0;
  let last = performance.now();
  const animate = () => {
    raf = requestAnimationFrame(animate);
    const now = performance.now();
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    frame += 1;

    if (moveAnim) {
      moveAnim.t += dt;
      const u = Math.min(1, moveAnim.t / moveAnim.duration);
      const ease = u * u * (3 - 2 * u);
      const mesh = meshById.get(moveAnim.id);
      if (mesh) {
        mesh.position.lerpVectors(moveAnim.from, moveAnim.to, ease);
        mesh.userData.baseY = mesh.position.y;
        selectionRing.position.set(mesh.position.x, moveAnim.to.y, mesh.position.z);
      }
      if (u >= 1) {
        const unit = unitById.get(moveAnim.id);
        if (unit && mesh) {
          mesh.position.copy(moveAnim.to);
          mesh.userData.baseY = moveAnim.to.y;
          clearPath();
          refreshSelectionVisual();
        }
        moveAnim = null;
      }
    }

    for (const [id, mesh] of meshById) {
      if (moveAnim?.id === id) continue;
      const kind = mesh.name.replace('unit:', '') as LiveUnitKind;
      const baseY = (mesh.userData.baseY as number) ?? 0.16;
      if (kind === 'drone' || kind === 'agent' || kind === 'swarm') {
        mesh.position.y = baseY + Math.sin(frame * 0.05 + mesh.position.x) * 0.05;
      }
    }

    // Gentle water shimmer
    for (const tile of hexByKey.values()) {
      if (tile.biome !== 'water') continue;
      const pulse = 0.78 + Math.sin(frame * 0.03 + tile.q) * 0.06;
      tile.topMat.opacity = pulse;
    }

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
  animate();

  setSelectedId('u3');

  return {
    setSelectedId,
    destroy: () => {
      cancelAnimationFrame(raf);
      renderer.domElement.removeEventListener('pointerdown', onPointerDown);
      renderer.domElement.removeEventListener('pointermove', onPointerMove);
      renderer.domElement.removeEventListener('pointerup', onPointerUp);
      controls.dispose();
      renderer.dispose();
      if (renderer.domElement.parentElement === host) host.removeChild(renderer.domElement);
    },
  };
}

export { UNIT_LABELS };
