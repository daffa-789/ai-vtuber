import { resolve } from "node:path";
import { normalizePath } from "vite";
delete process.env.ELECTRON_RUN_AS_NODE;
import { defineConfig, externalizeDepsPlugin } from "electron-vite";
import vue from "@vitejs/plugin-vue";
import vueJsx from "@vitejs/plugin-vue-jsx";
import { viteStaticCopy } from "vite-plugin-static-copy";
var stdin_default = defineConfig({
  main: {
    ssr: { noExternal: true },
    build: { rollupOptions: {
      input: resolve(__dirname, "src/main/index.js"),
      // Proses utama hanya menjalankan proses Node, jadi tidak ada paket
      // workspace yang perlu dibundel ke sini.
      external: (id) => id === "electron" || id.startsWith("node:")
    } }
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: {
      rollupOptions: {
        input: resolve(__dirname, "src/preload/index.js"),
        output: { entryFileNames: "[name].js" }
      }
    }
  },
  renderer: {
    root: resolve(__dirname, "renderer"),
    // Sumber `VITE_*` ada di `.env` akar repo. Kunci `VTUBER_*` otomatis tidak
    // terekspos ke bundel klien.
    envDir: resolve(__dirname, "../../"),
    publicDir: resolve(__dirname, "../../public"),
    resolve: { alias: {
      "@silverwolf/audio": resolve(__dirname, "../../packages/audio/src"),
      "@silverwolf/core-character": resolve(__dirname, "../../packages/core-character/src"),
      "@silverwolf/pipelines-audio": resolve(__dirname, "../../packages/pipelines-audio/src"),
      "@silverwolf/provider-inference": resolve(__dirname, "../../packages/provider-inference/src"),
      "@silverwolf/stage-ui": resolve(__dirname, "../../packages/stage-ui/src"),
      "@silverwolf/stage-ui-live2d": resolve(__dirname, "../../packages/stage-ui-live2d/src")
    } },
    plugins: [vue(), vueJsx(), viteStaticCopy({ targets: [
      { src: normalizePath(resolve(__dirname, "../../node_modules/onnxruntime-web/dist/*.wasm")), dest: "onnx" },
      { src: normalizePath(resolve(__dirname, "../../node_modules/piper-tts-web/dist/piper/*")), dest: "piper" }
    ] })],
    build: { rollupOptions: { input: resolve(__dirname, "renderer/index.html") } }
  }
});
export {
  stdin_default as default
};
