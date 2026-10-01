import { resolve } from 'node:path'
import { defineConfig, normalizePath } from 'vite'
import vue from '@vitejs/plugin-vue'
import { viteStaticCopy } from 'vite-plugin-static-copy'
export default defineConfig({
  plugins: [
    vue(),
    viteStaticCopy({ targets: [
      { src: normalizePath(resolve(__dirname, 'node_modules/onnxruntime-web/dist/*.wasm')), dest: 'onnx' },
      { src: normalizePath(resolve(__dirname, 'node_modules/piper-tts-web/dist/piper/*')), dest: 'piper' },
    ] }),
  ],
  // Aset berlisensi tetap berada di public/ root dan tidak pernah masuk bundle/git.
  publicDir: '../../public',
  server: {
    host: '0.0.0.0', allowedHosts: true,
    proxy: {
      '/api': { target: process.env.VTUBER_SIDECAR_URL ?? 'http://127.0.0.1:8787', changeOrigin: true },
      '/assets': { target: process.env.VTUBER_SIDECAR_URL ?? 'http://127.0.0.1:8787', changeOrigin: true },
    },
  },
})
