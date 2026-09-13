import * as THREE from 'three';
import type { Cloud, SpriteKind } from '@stateboard/tf-cost';
import { createSelectionRing as createLiveSelectionRing } from '../live/liveSprites';
import { GROUP_META } from './resourceGroups';

const SIZE = 128;
const cache = new Map<string, THREE.CanvasTexture>();

const CLOUD_BADGE: Record<Cloud, { fill: string; accent: string; label: string }> = {
  aws: { fill: '#232f3e', accent: '#ff9900', label: 'aws' },
  azure: { fill: '#0b1f3a', accent: '#0078d4', label: 'az' },
  gcp: { fill: '#1a2332', accent: '#ea4335', label: 'gcp' },
  other: { fill: '#1e293b', accent: '#94a3b8', label: 'tf' },
};

function softShadow(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number) {
  const g = ctx.createRadialGradient(cx, cy, 2, cx, cy, r);
  g.addColorStop(0, 'rgba(0,0,0,0.5)');
  g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.ellipse(cx, cy, r * 1.15, r * 0.42, 0, 0, Math.PI * 2);
  ctx.fill();
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

function drawCloudBadge(ctx: CanvasRenderingContext2D, cloud: Cloud) {
  const c = CLOUD_BADGE[cloud];
  const x = SIZE - 44;
  const y = 8;
  roundRect(ctx, x, y, 36, 22, 6);
  ctx.fillStyle = c.fill;
  ctx.fill();
  ctx.strokeStyle = c.accent;
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = c.accent;
  ctx.font = '700 11px ui-sans-serif, system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(c.label.toUpperCase(), x + 18, y + 12);
}

function drawGroupBadge(ctx: CanvasRenderingContext2D, kind: SpriteKind) {
  const g = GROUP_META[kind] ?? GROUP_META.generic;
  roundRect(ctx, 8, 8, 40, 22, 6);
  ctx.fillStyle = g.fill;
  ctx.fill();
  ctx.strokeStyle = g.accent;
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = g.accent;
  ctx.font = '700 10px ui-sans-serif, system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(g.short, 28, 20);
}

function drawComputeLogo(ctx: CanvasRenderingContext2D, cx: number, cy: number, accent: string) {
  roundRect(ctx, cx - 28, cy - 22, 56, 44, 6);
  ctx.fillStyle = '#1a2430';
  ctx.fill();
  ctx.strokeStyle = accent;
  ctx.lineWidth = 3;
  ctx.stroke();
  for (const yy of [cy - 10, cy + 2, cy + 14]) {
    ctx.fillStyle = accent;
    ctx.globalAlpha = 0.9;
    ctx.fillRect(cx - 18, yy - 2, 36, 4);
    ctx.globalAlpha = 1;
    ctx.beginPath();
    ctx.arc(cx + 20, yy, 3, 0, Math.PI * 2);
    ctx.fillStyle = '#fff';
    ctx.fill();
  }
}

function drawDatabaseLogo(ctx: CanvasRenderingContext2D, cx: number, cy: number, accent: string) {
  const g = ctx.createLinearGradient(cx, cy - 28, cx, cy + 28);
  g.addColorStop(0, accent);
  g.addColorStop(1, '#1e293b');
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.ellipse(cx, cy - 18, 26, 10, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillRect(cx - 26, cy - 18, 52, 36);
  ctx.beginPath();
  ctx.ellipse(cx, cy + 18, 26, 10, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,0.4)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.ellipse(cx, cy - 18, 26, 10, 0, 0, Math.PI * 2);
  ctx.stroke();
  ctx.beginPath();
  ctx.ellipse(cx, cy - 2, 26, 10, 0, Math.PI * 0.05, Math.PI - 0.05);
  ctx.stroke();
}

function drawStorageLogo(ctx: CanvasRenderingContext2D, cx: number, cy: number, accent: string) {
  ctx.fillStyle = '#1a2430';
  ctx.beginPath();
  ctx.moveTo(cx - 30, cy - 8);
  ctx.lineTo(cx - 24, cy + 26);
  ctx.quadraticCurveTo(cx, cy + 34, cx + 24, cy + 26);
  ctx.lineTo(cx + 30, cy - 8);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = accent;
  ctx.lineWidth = 3;
  ctx.stroke();
  ctx.fillStyle = accent;
  ctx.beginPath();
  ctx.ellipse(cx, cy - 12, 32, 12, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.25)';
  ctx.beginPath();
  ctx.ellipse(cx - 6, cy - 16, 10, 4, -0.3, 0, Math.PI * 2);
  ctx.fill();
}

function drawNetworkLogo(ctx: CanvasRenderingContext2D, cx: number, cy: number, accent: string) {
  ctx.strokeStyle = accent;
  ctx.lineWidth = 3;
  const nodes: [number, number][] = [
    [0, -26],
    [24, -6],
    [16, 24],
    [-16, 24],
    [-24, -6],
  ];
  for (const [dx, dy] of nodes) {
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + dx, cy + dy);
    ctx.stroke();
  }
  ctx.fillStyle = '#1a2430';
  ctx.beginPath();
  ctx.arc(cx, cy, 12, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = accent;
  ctx.lineWidth = 3;
  ctx.stroke();
  for (const [dx, dy] of nodes) {
    ctx.fillStyle = accent;
    ctx.beginPath();
    ctx.arc(cx + dx, cy + dy, 7, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawIdentityLogo(ctx: CanvasRenderingContext2D, cx: number, cy: number, accent: string) {
  ctx.fillStyle = accent;
  ctx.beginPath();
  ctx.arc(cx - 10, cy - 4, 16, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#0b1520';
  ctx.beginPath();
  ctx.arc(cx - 10, cy - 4, 7, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = accent;
  ctx.fillRect(cx - 2, cy - 8, 34, 10);
  ctx.fillRect(cx + 20, cy + 2, 8, 12);
  ctx.fillRect(cx + 10, cy + 2, 8, 8);
}

function drawGenericLogo(ctx: CanvasRenderingContext2D, cx: number, cy: number, accent: string) {
  ctx.fillStyle = '#1a2430';
  hexPath(ctx, cx, cy + 4, 30);
  ctx.fill();
  ctx.strokeStyle = accent;
  ctx.lineWidth = 3;
  hexPath(ctx, cx, cy + 4, 30);
  ctx.stroke();
  ctx.fillStyle = accent;
  hexPath(ctx, cx, cy - 4, 14);
  ctx.fill();
}

function drawKind(ctx: CanvasRenderingContext2D, kind: SpriteKind, cloud: Cloud) {
  const cx = SIZE / 2;
  const cy = SIZE / 2 + 10;
  const meta = GROUP_META[kind] ?? GROUP_META.generic;
  const accent = meta.accent;

  softShadow(ctx, cx, cy + 30, 38);

  const plate = ctx.createLinearGradient(cx, cy - 42, cx, cy + 42);
  plate.addColorStop(0, meta.fill);
  plate.addColorStop(1, 'rgba(8,16,28,0.95)');
  ctx.fillStyle = plate;
  roundRect(ctx, cx - 48, cy - 42, 96, 84, 14);
  ctx.fill();
  ctx.strokeStyle = accent;
  ctx.lineWidth = 2.5;
  roundRect(ctx, cx - 48, cy - 42, 96, 84, 14);
  ctx.stroke();

  switch (kind) {
    case 'compute':
      drawComputeLogo(ctx, cx, cy, accent);
      break;
    case 'database':
      drawDatabaseLogo(ctx, cx, cy, accent);
      break;
    case 'storage':
      drawStorageLogo(ctx, cx, cy, accent);
      break;
    case 'network':
      drawNetworkLogo(ctx, cx, cy, accent);
      break;
    case 'identity':
      drawIdentityLogo(ctx, cx, cy, accent);
      break;
    default:
      drawGenericLogo(ctx, cx, cy, accent);
  }

  drawGroupBadge(ctx, kind);
  drawCloudBadge(ctx, cloud);
}

function texture(kind: SpriteKind, cloud: Cloud): THREE.CanvasTexture {
  const key = `logo-group:${kind}:${cloud}`;
  let tex = cache.get(key);
  if (tex) return tex;
  const canvas = document.createElement('canvas');
  canvas.width = SIZE;
  canvas.height = SIZE;
  const ctx = canvas.getContext('2d')!;
  ctx.clearRect(0, 0, SIZE, SIZE);
  drawKind(ctx, kind, cloud);
  tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.needsUpdate = true;
  cache.set(key, tex);
  return tex;
}

export function tfSpriteDataUrl(kind: SpriteKind, cloud: Cloud = 'aws'): string {
  const canvas = document.createElement('canvas');
  canvas.width = SIZE;
  canvas.height = SIZE;
  const ctx = canvas.getContext('2d')!;
  drawKind(ctx, kind, cloud);
  return canvas.toDataURL('image/png');
}

export function createTfResourceSprite(
  kind: SpriteKind,
  cloud: Cloud,
  monthlyUsd: number,
  maxCost: number,
): THREE.Group {
  const g = new THREE.Group();
  g.name = `tf-logo:${kind}`;
  const meta = GROUP_META[kind] ?? GROUP_META.generic;

  const mat = new THREE.SpriteMaterial({
    map: texture(kind, cloud),
    transparent: true,
    depthWrite: false,
  });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(1.05, 1.05, 1);
  sprite.center.set(0.5, 0.12);
  sprite.position.y = 0.42;
  sprite.name = 'body';
  g.add(sprite);

  const hpCanvas = document.createElement('canvas');
  hpCanvas.width = 64;
  hpCanvas.height = 8;
  const hpCtx = hpCanvas.getContext('2d')!;
  hpCtx.fillStyle = 'rgba(11,26,40,0.85)';
  hpCtx.fillRect(0, 1, 64, 6);
  const t = maxCost > 0 ? Math.min(1, monthlyUsd / maxCost) : 0;
  hpCtx.fillStyle = meta.accent;
  hpCtx.fillRect(1, 2, Math.max(2, 62 * Math.max(0.05, t)), 4);
  const hpTex = new THREE.CanvasTexture(hpCanvas);
  const hp = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: hpTex, transparent: true, depthWrite: false }),
  );
  hp.scale.set(0.55, 0.08, 1);
  hp.position.y = 1.05;
  hp.name = 'cost-bar';
  g.add(hp);

  return g;
}

export function createSelectionRing(): THREE.Group {
  return createLiveSelectionRing();
}
