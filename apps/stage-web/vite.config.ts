import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({
  plugins: [vue()],
  // Aset berlisensi tetap berada di public/ root dan tidak pernah masuk bundle/git.
  publicDir: '../../public',
  server: { host: '0.0.0.0', allowedHosts: true, proxy: { '/api': { target: process.env.VTUBER_SIDECAR_URL ?? 'http://127.0.0.1:8787', changeOrigin: true } } },
})
