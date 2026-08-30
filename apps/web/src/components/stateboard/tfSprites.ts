import * as THREE from 'three';
import type { Cloud, SpriteKind } from '@stateboard/tf-cost';

const SIZE = 128;
const cache = new Map<string, THREE.CanvasTexture>();

const CLOUD_RGB: Record<Cloud, string> = {
  aws: 'rgb(236,106,6)',
  azure: 'rgb(76,215,246)',
  gcp: 'rgb(45,212,191)',
  other: 'rgb(148,163,184)',
};

function softShadow(ctx: CanvasRenderingContext2D, cx: number, cy: number) {
  const g = ctx.createRadialGradient(cx, cy + 20, 2, cx, cy + 20, 36);
  g.addColorStop(0, 'rgba(0,0,0,0.4)');
  g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.ellipse(cx, cy + 22, 34, 14, 0, 0, Math.PI * 2);
  ctx.fill();
}

function drawKind(ctx: CanvasRenderingContext2D, kind: SpriteKind, cloud: Cloud) {
  const cx = SIZE / 2;
  const cy = SIZE / 2 + 4;
  softShadow(ctx, cx, cy);
  const accent = CLOUD_RGB[cloud];

  switch (kind) {
    case 'compute': {
      ctx.fillStyle = '#9aa3ad';
      ctx.beginPath();
      ctx.moveTo(cx, cy - 28);
      ctx.lineTo(cx + 28, cy);
      ctx.lineTo(cx, cy + 28);
      ctx.lineTo(cx - 28, cy);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = accent;
      ctx.lineWidth = 3;
      ctx.stroke();
      break;
    }
    case 'network': {
      ctx.strokeStyle = accent;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(cx, cy + 18);
      ctx.lineTo(cx, cy - 20);
      ctx.stroke();
      ctx.beginPath();
      ctx.ellipse(cx + 4, cy - 24, 18, 10, -0.35, 0, Math.PI * 2);
      ctx.stroke();
      break;
    }
    case 'storage': {
      ctx.fillStyle = '#2a3544';
      ctx.fillRect(cx - 26, cy - 26, 52, 52);
      ctx.strokeStyle = accent;
      ctx.lineWidth = 3;
      ctx.strokeRect(cx - 26, cy - 26, 52, 52);
      ctx.fillStyle = accent;
      ctx.beginPath();
      ctx.moveTo(cx, cy - 14);
      ctx.lineTo(cx + 12, cy - 4);
      ctx.lineTo(cx + 8, cy + 14);
      ctx.lineTo(cx, cy + 18);
      ctx.lineTo(cx - 8, cy + 14);
      ctx.lineTo(cx - 12, cy - 4);
      ctx.closePath();
      ctx.fill();
      break;
    }
    case 'database': {
      const g = ctx.createLinearGradient(cx, cy - 30, cx, cy + 28);
      g.addColorStop(0, accent);
      g.addColorStop(1, '#1e293b');
      ctx.fillStyle = g;
      ctx.fillRect(cx - 22, cy - 18, 16, 44);
      ctx.fillRect(cx + 6, cy - 18, 16, 44);
      break;
    }
    case 'identity': {
      const g = ctx.createRadialGradient(cx, cy, 2, cx, cy, 26);
      g.addColorStop(0, '#fff');
      g.addColorStop(0.4, accent);
      g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(cx, cy, 24, 0, Math.PI * 2);
      ctx.fill();
      break;
    }
    default: {
      ctx.fillStyle = '#64748b';
      ctx.beginPath();
      ctx.moveTo(cx, cy - 24);
      ctx.lineTo(cx + 20, cy + 20);
      ctx.lineTo(cx - 20, cy + 20);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = accent;
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }
}

function texture(kind: SpriteKind, cloud: Cloud): THREE.CanvasTexture {
  const key = `${kind}:${cloud}`;
  let tex = cache.get(key);
  if (tex) return tex;
  const canvas = document.createElement('canvas');
  canvas.width = SIZE;
  canvas.height = SIZE;
  const ctx = canvas.getContext('2d')!;
  drawKind(ctx, kind, cloud);
  tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.needsUpdate = true;
  cache.set(key, tex);
  return tex;
}

export function createTfResourceSprite(
  kind: SpriteKind,
  cloud: Cloud,
  monthlyUsd: number,
  maxCost: number,
): THREE.Group {
  const g = new THREE.Group();
  const mat = new THREE.SpriteMaterial({
    map: texture(kind, cloud),
    transparent: true,
    depthWrite: false,
  });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(1.25, 1.25, 1);
  sprite.center.set(0.5, 0.2);
  sprite.position.y = 0.5;
  g.add(sprite);

  // Cost bar
  const hpCanvas = document.createElement('canvas');
  hpCanvas.width = 64;
  hpCanvas.height = 8;
  const hpCtx = hpCanvas.getContext('2d')!;
  hpCtx.fillStyle = 'rgba(11,26,40,0.85)';
  hpCtx.fillRect(0, 1, 64, 6);
  const t = maxCost > 0 ? Math.min(1, monthlyUsd / maxCost) : 0;
  hpCtx.fillStyle = '#5eead4';
  hpCtx.fillRect(1, 2, Math.max(2, 62 * t), 4);
  const hpTex = new THREE.CanvasTexture(hpCanvas);
  const hp = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: hpTex, transparent: true, depthWrite: false }),
  );
  hp.scale.set(0.65, 0.09, 1);
  hp.position.y = 1.15;
  g.add(hp);

  return g;
}

export function createSelectionRing(): THREE.Group {
  const g = new THREE.Group();
  const R = 0.7;
  const pts = Array.from({ length: 7 }, (_, i) => {
    const a = (Math.PI / 180) * (60 * i - 30);
    return new THREE.Vector3(R * Math.cos(a), 0.04, R * Math.sin(a));
  });
  g.add(
    new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineBasicMaterial({ color: 0xffffff }),
    ),
  );
  return g;
}
