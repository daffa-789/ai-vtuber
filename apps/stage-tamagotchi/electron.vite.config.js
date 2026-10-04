import fs from "node:fs";
import { resolve } from "node:path";
import { normalizePath } from "vite";
delete process.env.ELECTRON_RUN_AS_NODE;
import { defineConfig, externalizeDepsPlugin } from "electron-vite";
import vue from "@vitejs/plugin-vue";
import vueJsx from "@vitejs/plugin-vue-jsx";
import { viteStaticCopy } from "vite-plugin-static-copy";

function serveRepoAssets() {
  const assetsDir = resolve(__dirname, "../../assets");
  const publicDir = resolve(__dirname, "../../public");
  const mimeTypes = {
    ".onnx": "application/octet-stream",
    ".data": "application/octet-stream",
    ".wasm": "application/wasm",
    ".json": "application/json",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".png": "image/png",
    ".wav": "audio/wav"
  };

  return {
    name: "serve-repo-assets",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = req.url.split("?")[0];
        let filePath = null;
        if (url.startsWith("/assets/")) {
          filePath = resolve(assetsDir, url.slice("/assets/".length));
        } else if (url.startsWith("/onnx/")) {
          filePath = resolve(publicDir, "onnx", url.slice("/onnx/".length));
        } else if (url.startsWith("/piper/")) {
          filePath = resolve(publicDir, "piper", url.slice("/piper/".length));
        }

        if (filePath && fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
          const stat = fs.statSync(filePath);
          const ext = filePath.slice(filePath.lastIndexOf(".")).toLowerCase();
          res.setHeader("Content-Type", mimeTypes[ext] || "application/octet-stream");
          res.setHeader("Content-Length", stat.size);
          res.setHeader("Access-Control-Allow-Origin", "*");
          res.setHeader("Cross-Origin-Resource-Policy", "cross-origin");
          const stream = fs.createReadStream(filePath);
          return stream.pipe(res);
        }
        next();
      });
    }
  };
}

var stdin_default = defineConfig({
  main: {
    ssr: { noExternal: true },
    build: { rollupOptions: {
      input: resolve(__dirname, "src/main/index.js"),
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
    envDir: resolve(__dirname, "../../"),
    publicDir: resolve(__dirname, "../../public"),
    server: {
      headers: {
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Embedder-Policy": "require-corp"
      }
    },
    resolve: { alias: {
      "@silverwolf/audio": resolve(__dirname, "../../packages/audio/src"),
      "@silverwolf/core-character": resolve(__dirname, "../../packages/core-character/src"),
      "@silverwolf/pipelines-audio": resolve(__dirname, "../../packages/pipelines-audio/src"),
      "@silverwolf/provider-inference": resolve(__dirname, "../../packages/provider-inference/src"),
      "@silverwolf/stage-ui": resolve(__dirname, "../../packages/stage-ui/src"),
      "@silverwolf/stage-ui-live2d": resolve(__dirname, "../../packages/stage-ui-live2d/src")
    } },
    plugins: [
      serveRepoAssets(),
      vue(),
      vueJsx(),
      viteStaticCopy({ targets: [
        { src: normalizePath(resolve(__dirname, "../../node_modules/onnxruntime-web/dist/ort-wasm*")), dest: "onnx" },
        { src: normalizePath(resolve(__dirname, "../../node_modules/piper-tts-web/dist/piper/*")), dest: "piper" }
      ] })
    ],
    build: { rollupOptions: { input: resolve(__dirname, "renderer/index.html") } }
  }
});
export {
  stdin_default as default
};
