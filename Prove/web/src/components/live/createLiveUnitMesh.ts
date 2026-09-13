import * as THREE from 'three';
import {
  ERA_ACCENT,
  type LiveBuildingKind,
  type LiveTeam,
  type LiveUnitKind,
} from './liveUnitKinds';

const HP_CYAN = 0x5eead4;
const HP_BG = 0x0b1a28;

function lit(color: number, opts?: { emissive?: number; emissiveIntensity?: number; opacity?: number; metal?: number }) {
  const opacity = opts?.opacity ?? 1;
  return new THREE.MeshStandardMaterial({
    color,
    roughness: opts?.metal ? 0.35 : 0.55,
    metalness: opts?.metal ?? 0.15,
    emissive: opts?.emissive ?? 0x000000,
    emissiveIntensity: opts?.emissiveIntensity ?? 0,
    transparent: opacity < 1,
    opacity,
    flatShading: true,
  });
}

function glowSprite(color: number, scale: number): THREE.Sprite {
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext('2d')!;
  const g = ctx.createRadialGradient(32, 32, 2, 32, 32, 30);
  const c = new THREE.Color(color);
  g.addColorStop(0, `rgba(${Math.round(c.r * 255)},${Math.round(c.g * 255)},${Math.round(c.b * 255)},0.55)`);
  g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  const tex = new THREE.CanvasTexture(canvas);
  const mat = new THREE.SpriteMaterial({
    map: tex,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const spr = new THREE.Sprite(mat);
  spr.scale.set(scale, scale, 1);
  return spr;
}

function shadowDisc(r = 0.35): THREE.Mesh {
  const m = new THREE.Mesh(
    new THREE.CircleGeometry(r, 24),
    new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.35, depthWrite: false }),
  );
  m.rotation.x = -Math.PI / 2;
  m.position.y = 0.02;
  return m;
}

/** Build a unit token group centered at origin — silhouettes match concept sheet. */
export function createLiveUnitMesh(kind: LiveUnitKind, _team: LiveTeam, stack = 1): THREE.Group {
  const g = new THREE.Group();
  g.name = `unit:${kind}`;
  g.add(shadowDisc(kind === 'nano' ? 0.45 : 0.32));

  switch (kind) {
    case 'pioneer': {
      const body = new THREE.Mesh(new THREE.ConeGeometry(0.2, 0.42, 4), lit(0xc4a574, { metal: 0.2 }));
      body.rotation.y = Math.PI / 4;
      body.position.y = 0.28;
      g.add(body);
      break;
    }
    case 'drone': {
      // Flat grey diamond + cyan engine trail (concept)
      const body = new THREE.Mesh(
        new THREE.OctahedronGeometry(0.32, 0),
        lit(0x8a93a0, { metal: 0.45, emissive: 0x1a3040, emissiveIntensity: 0.15 }),
      );
      body.position.y = 0.48;
      body.scale.set(1.15, 0.35, 0.85);
      body.rotation.y = Math.PI / 4;
      g.add(body);
      const trail = new THREE.Mesh(
        new THREE.ConeGeometry(0.1, 0.55, 8),
        lit(ERA_ACCENT.tts4, { emissive: ERA_ACCENT.tts4, emissiveIntensity: 0.9, opacity: 0.75 }),
      );
      trail.rotation.x = Math.PI / 2;
      trail.position.set(0, 0.48, 0.42);
      g.add(trail);
      const glow = glowSprite(ERA_ACCENT.tts4, 0.9);
      glow.position.set(0, 0.48, 0.55);
      g.add(glow);
      break;
    }
    case 'cyber': {
      // Twin upright neon-orange bars
      const barMat = lit(0xff9a3c, { emissive: 0xff6a00, emissiveIntensity: 0.65, metal: 0.2 });
      const barGeo = new THREE.BoxGeometry(0.16, 0.62, 0.16);
      const left = new THREE.Mesh(barGeo, barMat);
      left.position.set(-0.15, 0.38, 0);
      const right = new THREE.Mesh(barGeo, barMat);
      right.position.set(0.15, 0.38, 0);
      g.add(left, right);
      const glow = glowSprite(0xff8a2a, 1.1);
      glow.position.y = 0.45;
      g.add(glow);
      break;
    }
    case 'firewall': {
      // Dark cube + cyan shield faces
      const cube = new THREE.Mesh(
        new THREE.BoxGeometry(0.48, 0.42, 0.48),
        lit(0x2a3544, { metal: 0.55, emissive: 0x0a2030, emissiveIntensity: 0.2 }),
      );
      cube.position.y = 0.28;
      g.add(cube);
      const faceMat = lit(ERA_ACCENT.tts4, { emissive: ERA_ACCENT.tts4, emissiveIntensity: 0.7 });
      for (const [x, z] of [
        [0, 0.245],
        [0, -0.245],
        [0.245, 0],
        [-0.245, 0],
      ] as const) {
        const plate = new THREE.Mesh(new THREE.PlaneGeometry(0.28, 0.28), faceMat);
        plate.position.set(x, 0.28, z);
        if (Math.abs(x) > 0) plate.rotation.y = Math.PI / 2;
        if (z < 0) plate.rotation.y = Math.PI;
        g.add(plate);
      }
      const top = new THREE.Mesh(new THREE.CircleGeometry(0.14, 6), faceMat);
      top.rotation.x = -Math.PI / 2;
      top.position.y = 0.5;
      g.add(top);
      break;
    }
    case 'battery': {
      const base = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.2, 0.36), lit(0x3d4a58, { metal: 0.4 }));
      base.position.y = 0.16;
      const gun = new THREE.Mesh(
        new THREE.BoxGeometry(0.14, 0.14, 0.5),
        lit(ERA_ACCENT.tts4, { emissive: ERA_ACCENT.tts4, emissiveIntensity: 0.5 }),
      );
      gun.position.set(0, 0.34, -0.06);
      gun.rotation.x = -0.4;
      g.add(base, gun);
      break;
    }
    case 'swarm': {
      const n = Math.min(5, Math.max(4, stack));
      const mat = lit(ERA_ACCENT.tts5, { emissive: ERA_ACCENT.tts5, emissiveIntensity: 0.85 });
      for (let i = 0; i < n; i++) {
        const a = (i / n) * Math.PI * 2 + 0.2;
        const dot = new THREE.Mesh(new THREE.SphereGeometry(0.1, 12, 10), mat);
        dot.position.set(Math.cos(a) * 0.24, 0.28 + (i % 2) * 0.08, Math.sin(a) * 0.24);
        g.add(dot);
      }
      const glow = glowSprite(ERA_ACCENT.tts5, 1.0);
      glow.position.y = 0.3;
      g.add(glow);
      break;
    }
    case 'agent': {
      const core = new THREE.Mesh(
        new THREE.SphereGeometry(0.2, 16, 14),
        lit(0xb8f0ff, { emissive: ERA_ACCENT.tts4, emissiveIntensity: 0.95 }),
      );
      core.position.y = 0.38;
      const pip = new THREE.Mesh(
        new THREE.SphereGeometry(0.07, 10, 8),
        lit(ERA_ACCENT.tts4, { emissive: ERA_ACCENT.tts4, emissiveIntensity: 1 }),
      );
      pip.position.set(0.3, 0.4, 0);
      pip.name = 'orbit-pip';
      g.add(core, pip);
      const glow = glowSprite(ERA_ACCENT.tts4, 1.2);
      glow.position.y = 0.38;
      g.add(glow);
      break;
    }
    case 'bio': {
      const spike = new THREE.Mesh(
        new THREE.ConeGeometry(0.18, 0.75, 5),
        lit(ERA_ACCENT.tts6, { emissive: 0x0d9488, emissiveIntensity: 0.45 }),
      );
      spike.position.y = 0.42;
      spike.rotation.z = 0.12;
      g.add(spike);
      break;
    }
    case 'nano': {
      const blob = new THREE.Mesh(
        new THREE.SphereGeometry(0.42, 20, 16),
        lit(ERA_ACCENT.tts6, { emissive: ERA_ACCENT.tts6, emissiveIntensity: 0.55, opacity: 0.45 }),
      );
      blob.position.y = 0.28;
      blob.scale.set(1.25, 0.55, 1.15);
      g.add(blob);
      const inner = new THREE.Mesh(
        new THREE.SphereGeometry(0.18, 12, 10),
        lit(0xa5f3fc, { emissive: ERA_ACCENT.tts4, emissiveIntensity: 0.7, opacity: 0.7 }),
      );
      inner.position.y = 0.28;
      g.add(inner);
      const glow = glowSprite(ERA_ACCENT.tts6, 1.4);
      glow.position.y = 0.28;
      g.add(glow);
      break;
    }
  }

  // Slim cyan HP bar (concept-style)
  const hpBg = new THREE.Mesh(
    new THREE.PlaneGeometry(0.5, 0.045),
    new THREE.MeshBasicMaterial({ color: HP_BG, depthTest: true, transparent: true, opacity: 0.85 }),
  );
  hpBg.position.set(0, 0.95, 0);
  hpBg.name = 'hp-bg';
  const hpFill = new THREE.Mesh(
    new THREE.PlaneGeometry(0.46, 0.03),
    new THREE.MeshBasicMaterial({ color: HP_CYAN, depthTest: true }),
  );
  hpFill.position.set(0, 0.97, 0.01);
  hpFill.name = 'hp-fill';
  g.add(hpBg, hpFill);

  return g;
}

export function setUnitHpBar(group: THREE.Group, hp01: number) {
  const fill = group.getObjectByName('hp-fill') as THREE.Mesh | undefined;
  if (!fill) return;
  const t = Math.max(0.05, Math.min(1, hp01));
  fill.scale.x = t;
  fill.position.x = -0.23 * (1 - t);
}

export function createLiveBuildingMesh(kind: LiveBuildingKind, _team: LiveTeam): THREE.Group {
  const g = new THREE.Group();
  g.name = `building:${kind}`;
  g.add(shadowDisc(0.55));

  const metal = lit(0x5a6570, { metal: 0.55, emissive: 0x1a2530, emissiveIntensity: 0.15 });
  const cyan = lit(ERA_ACCENT.tts4, { emissive: ERA_ACCENT.tts4, emissiveIntensity: 0.8, metal: 0.3 });

  if (kind === 'capital') {
    // Hex command platform + tall beacon beam
    const base = new THREE.Mesh(new THREE.CylinderGeometry(0.72, 0.78, 0.22, 6), metal);
    base.position.y = 0.14;
    base.rotation.y = Math.PI / 6;
    const mid = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.5, 0.35, 6), metal);
    mid.position.y = 0.4;
    mid.rotation.y = Math.PI / 6;
    const beam = new THREE.Mesh(
      new THREE.CylinderGeometry(0.07, 0.1, 1.4, 8),
      lit(ERA_ACCENT.tts4, { emissive: ERA_ACCENT.tts4, emissiveIntensity: 1.1, opacity: 0.85 }),
    );
    beam.position.y = 1.15;
    const glow = glowSprite(ERA_ACCENT.tts4, 1.8);
    glow.position.y = 1.6;
    g.add(base, mid, beam, glow);
  } else if (kind === 'outpost') {
    const pad = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.55, 0.1, 24), metal);
    pad.position.y = 0.08;
    g.add(pad);
    for (let i = 0; i < 3; i++) {
      const a = (i / 3) * Math.PI * 2;
      const post = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.05, 0.42, 8), cyan);
      post.position.set(Math.cos(a) * 0.28, 0.32, Math.sin(a) * 0.28);
      g.add(post);
    }
  } else {
    const pad = new THREE.Mesh(new THREE.CylinderGeometry(0.48, 0.52, 0.1, 6), metal);
    pad.position.y = 0.08;
    pad.rotation.y = Math.PI / 6;
    const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.05, 0.55, 6), cyan);
    mast.position.y = 0.4;
    const dish = new THREE.Mesh(new THREE.CircleGeometry(0.24, 20), cyan);
    dish.position.set(0, 0.62, 0.06);
    dish.rotation.x = -Math.PI / 3;
    g.add(pad, mast, dish);
  }

  return g;
}

/** White hex outline under selection — matches concept. */
export function createSelectionRing(): THREE.Group {
  const g = new THREE.Group();
  g.name = 'selection-ring';
  const pts: THREE.Vector3[] = [];
  const R = 0.72;
  for (let i = 0; i <= 6; i++) {
    const angle = (Math.PI / 180) * (60 * i - 30);
    pts.push(new THREE.Vector3(R * Math.cos(angle), 0.04, R * Math.sin(angle)));
  }
  const line = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(pts),
    new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.95 }),
  );
  g.add(line);
  const fill = new THREE.Mesh(
    new THREE.CircleGeometry(R * 0.92, 6),
    new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.08,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
  );
  fill.rotation.x = -Math.PI / 2;
  fill.rotation.z = Math.PI / 6;
  fill.position.y = 0.03;
  g.add(fill);
  return g;
}

export function createPathGhost(from: THREE.Vector3, to: THREE.Vector3): THREE.Line {
  const mid = from.clone().lerp(to, 0.5);
  mid.y += 0.55;
  const curve = new THREE.QuadraticBezierCurve3(
    from.clone().setY(0.12),
    mid,
    to.clone().setY(0.12),
  );
  const pts = curve.getPoints(20);
  const geo = new THREE.BufferGeometry().setFromPoints(pts);
  const mat = new THREE.LineDashedMaterial({
    color: 0x4cd7f6,
    dashSize: 0.18,
    gapSize: 0.12,
    transparent: true,
    opacity: 0.9,
  });
  const line = new THREE.Line(geo, mat);
  line.computeLineDistances();
  line.name = 'path-ghost';
  return line;
}
