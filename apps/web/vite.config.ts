import path from 'node:path';
import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '../..');

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@stateboard/tf-cost': path.resolve(root, 'packages/tf-cost/src/index.ts'),
    },
  },
  optimizeDeps: {
    include: ['three', 'three/addons/controls/OrbitControls.js'],
  },
  server: {
    port: 5173,
    fs: { allow: [root] },
  },
});
