import { resolve } from 'node:path'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import vue from '@vitejs/plugin-vue'
import { viteStaticCopy } from 'vite-plugin-static-copy'
const web = resolve(__dirname, '../stage-web')
export default defineConfig({
  main: {
    ssr: { noExternal: true },
    resolve: { alias: {
      '@silverwolf/core-config': resolve(__dirname, '../../packages/core-config/src/index.ts'),
      '@silverwolf/core-character': resolve(__dirname, '../../packages/core-character/src/index.ts'),
      '@silverwolf/core-agent': resolve(__dirname, '../../packages/core-agent/src/index.ts'),
      '@silverwolf/provider-inference': resolve(__dirname, '../../packages/provider-inference/src/index.ts'),
      '@silverwolf/server-shared': resolve(__dirname, '../../packages/server-shared/src/index.ts'),
      '@silverwolf/server-runtime': resolve(__dirname, '../../packages/server-runtime/src/index.ts'),
    } },
    build: { rollupOptions: {
    input: resolve(__dirname, 'src/main/index.ts'),
    // Hanya Electron dan builtin Node yang eksternal; seluruh paket workspace
    // dibundel agar installer tidak bergantung pada symlink pnpm.
    external: id => id === 'electron' || id.startsWith('node:'),
  } } },
  preload: { plugins: [externalizeDepsPlugin()], build: { rollupOptions: { input: resolve(__dirname, 'src/preload/index.ts') } } },
  renderer: {
    root: web,
    publicDir: resolve(__dirname, '../../public'),
    plugins: [vue(), viteStaticCopy({ targets: [
      { src: resolve(web, 'node_modules/onnxruntime-web/dist/*.wasm'), dest: 'onnx' },
      { src: resolve(web, 'node_modules/piper-tts-web/dist/piper/*'), dest: 'piper' },
    ] })],
    build: { rollupOptions: { input: resolve(web, 'index.html') } },
  },
})
