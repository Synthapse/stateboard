import * as THREE from 'three';
import {
  ERA_ACCENT,
  type LiveBuildingKind,
  type LiveUnitKind,
} from './liveUnitKinds';

const SIZE = 128;
const texCache = new Map<string, THREE.CanvasTexture>();

function hexRgb(n: number): string {
  const c = new THREE.Color(n);
  return `rgb(${Math.round(c.r * 255)},${Math.round(c.g * 255)},${Math.round(c.b * 255)})`;
}

function softShadow(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number) {
  const g = ctx.createRadialGradient(cx, cy, 2, cx, cy, r);
  g.addColorStop(0, 'rgba(0,0,0,0.45)');
  g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.ellipse(cx, cy, r * 1.1, r * 0.45, 0, 0, Math.PI * 2);
  ctx.fill();
}

function glow(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number, color: string, a = 0.55) {
  const g = ctx.createRadialGradient(cx, cy, 1, cx, cy, r);
  g.addColorStop(0, color.replace(')', `, ${a})`).replace('rgb', 'rgba'));
  g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fill();
}

/** Exported so Stateboard can paint the same RTS silhouettes. */
export function drawUnitIcon(ctx: CanvasRenderingContext2D, kind: LiveUnitKind) {
  const cx = SIZE / 2;
  const cy = SIZE / 2 + 8;
  softShadow(ctx, cx, cy + 28, 36);

  switch (kind) {
    case 'pioneer': {
      ctx.fillStyle = '#c4a574';
      ctx.beginPath();
      ctx.moveTo(cx, cy - 28);
      ctx.lineTo(cx + 18, cy + 22);
      ctx.lineTo(cx - 18, cy + 22);
      ctx.closePath();
      ctx.fill();
      break;
    }
    case 'drone': {
      // Flat grey diamond + cyan trail
      glow(ctx, cx + 28, cy + 4, 28, hexRgb(ERA_ACCENT.tts4), 0.5);
      ctx.fillStyle = '#9aa3ad';
      ctx.beginPath();
      ctx.moveTo(cx - 8, cy - 22);
      ctx.lineTo(cx + 26, cy);
      ctx.lineTo(cx - 8, cy + 22);
      ctx.lineTo(cx - 28, cy);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = '#c8d0d8';
      ctx.lineWidth = 2;
      ctx.stroke();
      // trail
      const tg = ctx.createLinearGradient(cx + 10, cy, cx + 52, cy);
      tg.addColorStop(0, 'rgba(76,215,246,0.9)');
      tg.addColorStop(1, 'rgba(76,215,246,0)');
      ctx.fillStyle = tg;
      ctx.beginPath();
      ctx.moveTo(cx + 8, cy - 8);
      ctx.lineTo(cx + 52, cy);
      ctx.lineTo(cx + 8, cy + 8);
      ctx.closePath();
      ctx.fill();
      break;
    }
    case 'cyber': {
      glow(ctx, cx, cy, 40, 'rgb(255,140,40)', 0.45);
      const drawBar = (x: number) => {
        const g = ctx.createLinearGradient(x, cy - 32, x, cy + 30);
        g.addColorStop(0, '#ffd08a');
        g.addColorStop(0.4, '#ff9a3c');
        g.addColorStop(1, '#ec6a06');
        ctx.fillStyle = g;
        ctx.fillRect(x - 9, cy - 32, 18, 62);
        ctx.fillStyle = 'rgba(255,255,255,0.25)';
        ctx.fillRect(x - 6, cy - 28, 5, 54);
      };
      drawBar(cx - 16);
      drawBar(cx + 16);
      break;
    }
    case 'firewall': {
      ctx.fillStyle = '#2a3544';
      roundRect(ctx, cx - 26, cy - 26, 52, 52, 6);
      ctx.fill();
      ctx.strokeStyle = hexRgb(ERA_ACCENT.tts4);
      ctx.lineWidth = 3;
      ctx.stroke();
      // shield glyph
      ctx.fillStyle = hexRgb(ERA_ACCENT.tts4);
      ctx.beginPath();
      ctx.moveTo(cx, cy - 16);
      ctx.lineTo(cx + 14, cy - 6);
      ctx.lineTo(cx + 10, cy + 14);
      ctx.lineTo(cx, cy + 20);
      ctx.lineTo(cx - 10, cy + 14);
      ctx.lineTo(cx - 14, cy - 6);
      ctx.closePath();
      ctx.fill();
      glow(ctx, cx, cy, 30, hexRgb(ERA_ACCENT.tts4), 0.35);
      break;
    }
    case 'battery': {
      ctx.fillStyle = '#3d4a58';
      roundRect(ctx, cx - 24, cy - 8, 48, 28, 4);
      ctx.fill();
      ctx.fillStyle = hexRgb(ERA_ACCENT.tts4);
      ctx.save();
      ctx.translate(cx + 4, cy - 4);
      ctx.rotate(-0.4);
      ctx.fillRect(-8, -28, 14, 40);
      ctx.restore();
      glow(ctx, cx + 10, cy - 18, 18, hexRgb(ERA_ACCENT.tts4), 0.4);
      break;
    }
    case 'swarm': {
      glow(ctx, cx, cy, 36, hexRgb(ERA_ACCENT.tts5), 0.4);
      const dots = [
        [0, -18],
        [18, 0],
        [0, 18],
        [-18, 0],
        [0, 0],
      ];
      for (const [dx, dy] of dots) {
        const g = ctx.createRadialGradient(cx + dx, cy + dy, 1, cx + dx, cy + dy, 12);
        g.addColorStop(0, '#e9d5ff');
        g.addColorStop(0.5, hexRgb(ERA_ACCENT.tts5));
        g.addColorStop(1, 'rgba(167,139,250,0.2)');
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(cx + dx, cy + dy, 11, 0, Math.PI * 2);
        ctx.fill();
      }
      break;
    }
    case 'agent': {
      glow(ctx, cx, cy, 42, hexRgb(ERA_ACCENT.tts4), 0.55);
      const core = ctx.createRadialGradient(cx - 4, cy - 6, 2, cx, cy, 22);
      core.addColorStop(0, '#ffffff');
      core.addColorStop(0.35, '#b8f0ff');
      core.addColorStop(1, hexRgb(ERA_ACCENT.tts4));
      ctx.fillStyle = core;
      ctx.beginPath();
      ctx.arc(cx, cy, 20, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#e0f7ff';
      ctx.beginPath();
      ctx.arc(cx + 26, cy - 6, 7, 0, Math.PI * 2);
      ctx.fill();
      break;
    }
    case 'bio': {
      glow(ctx, cx, cy, 30, hexRgb(ERA_ACCENT.tts6), 0.35);
      const g = ctx.createLinearGradient(cx, cy - 36, cx, cy + 28);
      g.addColorStop(0, '#99f6e4');
      g.addColorStop(1, hexRgb(ERA_ACCENT.tts6));
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.moveTo(cx + 4, cy - 36);
      ctx.lineTo(cx + 16, cy + 28);
      ctx.lineTo(cx - 14, cy + 22);
      ctx.closePath();
      ctx.fill();
      break;
    }
    case 'nano': {
      glow(ctx, cx, cy, 44, hexRgb(ERA_ACCENT.tts6), 0.45);
      const cloud = ctx.createRadialGradient(cx, cy, 4, cx, cy, 34);
      cloud.addColorStop(0, 'rgba(165,243,252,0.85)');
      cloud.addColorStop(0.45, 'rgba(45,212,191,0.45)');
      cloud.addColorStop(1, 'rgba(45,212,191,0)');
      ctx.fillStyle = cloud;
      ctx.beginPath();
      ctx.ellipse(cx, cy + 4, 38, 24, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = 'rgba(255,255,255,0.55)';
      ctx.beginPath();
      ctx.arc(cx - 6, cy - 2, 8, 0, Math.PI * 2);
      ctx.fill();
      break;
    }
  }
}

/** Exported so Stateboard can paint the same RTS building pads. */
export function drawBuildingIcon(ctx: CanvasRenderingContext2D, kind: LiveBuildingKind) {
  const cx = SIZE / 2;
  const cy = SIZE / 2 + 10;
  softShadow(ctx, cx, cy + 30, 40);

  if (kind === 'capital') {
    // Hex platform
    ctx.fillStyle = '#5a6570';
    hexPath(ctx, cx, cy + 18, 36);
    ctx.fill();
    ctx.fillStyle = '#3d4650';
    hexPath(ctx, cx, cy + 8, 26);
    ctx.fill();
    // Beacon beam
    const beam = ctx.createLinearGradient(cx, cy - 50, cx, cy + 10);
    beam.addColorStop(0, 'rgba(76,215,246,0)');
    beam.addColorStop(0.3, 'rgba(76,215,246,0.85)');
    beam.addColorStop(1, 'rgba(76,215,246,0.15)');
    ctx.fillStyle = beam;
    ctx.fillRect(cx - 6, cy - 52, 12, 70);
    glow(ctx, cx, cy - 20, 28, hexRgb(ERA_ACCENT.tts4), 0.5);
  } else if (kind === 'outpost') {
    ctx.fillStyle = '#5a6570';
    ctx.beginPath();
    ctx.arc(cx, cy + 16, 28, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = hexRgb(ERA_ACCENT.tts4);
    for (let i = 0; i < 3; i++) {
      const a = (i / 3) * Math.PI * 2 - Math.PI / 2;
      ctx.fillRect(cx + Math.cos(a) * 14 - 3, cy + 4 + Math.sin(a) * 10 - 14, 6, 28);
    }
  } else {
    ctx.fillStyle = '#5a6570';
    hexPath(ctx, cx, cy + 16, 30);
    ctx.fill();
    ctx.strokeStyle = hexRgb(ERA_ACCENT.tts4);
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(cx, cy + 10);
    ctx.lineTo(cx, cy - 18);
    ctx.stroke();
    ctx.beginPath();
    ctx.ellipse(cx + 2, cy - 22, 16, 10, -0.4, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function hexPath(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number) {
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 180) * (60 * i - 30);
    const x = cx + r * Math.cos(a);
    const y = cy + r * Math.sin(a);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

export function textureFor(key: string, draw: (ctx: CanvasRenderingContext2D) => void): THREE.CanvasTexture {
  let tex = texCache.get(key);
  if (tex) return tex;
  const canvas = document.createElement('canvas');
  canvas.width = SIZE;
  canvas.height = SIZE;
  const ctx = canvas.getContext('2d')!;
  ctx.clearRect(0, 0, SIZE, SIZE);
  draw(ctx);
  tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.needsUpdate = true;
  texCache.set(key, tex);
  return tex;
}

/** Data-URL for HUD / CSS background use. */
export function liveSpriteDataUrl(kind: LiveUnitKind | LiveBuildingKind, isBuilding = false): string {
  const canvas = document.createElement('canvas');
  canvas.width = SIZE;
  canvas.height = SIZE;
  const ctx = canvas.getContext('2d')!;
  if (isBuilding) drawBuildingIcon(ctx, kind as LiveBuildingKind);
  else drawUnitIcon(ctx, kind as LiveUnitKind);
  return canvas.toDataURL('image/png');
}

export function createUnitSprite(kind: LiveUnitKind, hp01: number): THREE.Group {
  const g = new THREE.Group();
  g.name = `unit:${kind}`;

  const tex = textureFor(`unit:${kind}`, (ctx) => drawUnitIcon(ctx, kind));
  const mat = new THREE.SpriteMaterial({
    map: tex,
    transparent: true,
    depthWrite: false,
  });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(1.35, 1.35, 1);
  sprite.center.set(0.5, 0.2);
  sprite.position.y = 0.55;
  sprite.name = 'body';
  g.add(sprite);

  // HP bar as tiny sprite strip
  const hpCanvas = document.createElement('canvas');
  hpCanvas.width = 64;
  hpCanvas.height = 8;
  const hpCtx = hpCanvas.getContext('2d')!;
  paintHp(hpCtx, hp01);
  const hpTex = new THREE.CanvasTexture(hpCanvas);
  hpTex.needsUpdate = true;
  const hpMat = new THREE.SpriteMaterial({ map: hpTex, transparent: true, depthWrite: false });
  const hp = new THREE.Sprite(hpMat);
  hp.scale.set(0.7, 0.1, 1);
  hp.position.y = 1.25;
  hp.name = 'hp-sprite';
  hp.userData.hpCanvas = hpCanvas;
  hp.userData.hpCtx = hpCtx;
  hp.userData.hpTex = hpTex;
  g.add(hp);

  return g;
}

function paintHp(ctx: CanvasRenderingContext2D, hp01: number) {
  ctx.clearRect(0, 0, 64, 8);
  ctx.fillStyle = 'rgba(11,26,40,0.85)';
  ctx.fillRect(0, 1, 64, 6);
  const t = Math.max(0.05, Math.min(1, hp01));
  ctx.fillStyle = '#5eead4';
  ctx.fillRect(1, 2, 62 * t, 4);
}

export function setSpriteHp(group: THREE.Group, hp01: number) {
  const hp = group.getObjectByName('hp-sprite') as THREE.Sprite | undefined;
  if (!hp) return;
  const ctx = hp.userData.hpCtx as CanvasRenderingContext2D | undefined;
  const tex = hp.userData.hpTex as THREE.CanvasTexture | undefined;
  if (!ctx || !tex) return;
  paintHp(ctx, hp01);
  tex.needsUpdate = true;
}

export function createBuildingSprite(kind: LiveBuildingKind): THREE.Group {
  const g = new THREE.Group();
  g.name = `building:${kind}`;
  const tex = textureFor(`building:${kind}`, (ctx) => drawBuildingIcon(ctx, kind));
  const mat = new THREE.SpriteMaterial({
    map: tex,
    transparent: true,
    depthWrite: false,
  });
  const sprite = new THREE.Sprite(mat);
  const scale = kind === 'capital' ? 1.85 : 1.45;
  sprite.scale.set(scale, scale, 1);
  sprite.center.set(0.5, 0.15);
  sprite.position.y = kind === 'capital' ? 0.75 : 0.55;
  g.add(sprite);
  return g;
}

export function createSelectionRing(): THREE.Group {
  const g = new THREE.Group();
  g.name = 'selection-ring';
  const pts: THREE.Vector3[] = [];
  const R = 0.72;
  for (let i = 0; i <= 6; i++) {
    const angle = (Math.PI / 180) * (60 * i - 30);
    pts.push(new THREE.Vector3(R * Math.cos(angle), 0.04, R * Math.sin(angle)));
  }
  g.add(
    new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.95 }),
    ),
  );
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
  const geo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(20));
  const line = new THREE.Line(
    geo,
    new THREE.LineDashedMaterial({
      color: 0x4cd7f6,
      dashSize: 0.18,
      gapSize: 0.12,
      transparent: true,
      opacity: 0.9,
    }),
  );
  line.computeLineDistances();
  line.name = 'path-ghost';
  return line;
}
