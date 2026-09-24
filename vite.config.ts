import { createReadStream, existsSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { defineConfig, loadEnv, type Plugin } from 'vite';

/**
 * onnxruntime-web mengimpor glue-nya dengan akhiran `?import`, dan Vite menanggapi
 * query itu dengan mencoba mentransformasi file sebagai modul sumber -> 500.
 * File di public/ sebenarnya sudah tersaji benar tanpa query, jadi cukup
 * lepaskan query untuk jalur /ort/ saja.
 */
function sajikanAsetOrt(): Plugin {
  const akar = resolve('public');
  const batasan = join(akar, 'ort');

  return {
    name: 'sajikan-aset-ort',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = req.url ?? '';
        if (!url.startsWith('/ort/') || !url.includes('?')) return next();

        const berkas = join(akar, decodeURIComponent(url.slice(1).split('?')[0]));
        // Tolak jalur yang keluar dari public/ort.
        if (!berkas.startsWith(batasan) || !existsSync(berkas) || !statSync(berkas).isFile()) {
          return next();
        }

        res.setHeader(
          'content-type',
          berkas.endsWith('.mjs') ? 'text/javascript' : 'application/wasm',
        );
        createReadStream(berkas).pipe(res);
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  // Port sidecar dibaca dari satu tempat (.env VTUBER_PORT) supaya proxy tidak
  // pernah menunjuk ke proses proyek lain saat portnya berpindah.
  const env = loadEnv(mode, process.cwd(), 'VTUBER_');
  const sidecar = env.VTUBER_PORT || '8787';

  return {
    plugins: [sajikanAsetOrt()],
    server: {
      port: Number(env.VTUBER_DEV_PORT) || 5173,
      proxy: { '/api': { target: `http://127.0.0.1:${sidecar}`, changeOrigin: false } },
      // Model .moc3 sering sedang dipegang Live2D Viewer / VTube Studio, dan
      // watcher yang menabrak file terkunci membuat seluruh dev server mati
      // (EBUSY), bukan cuma melewatkan satu file.
      watch: {
        ignored: ['**/public/models/**', '**/public/ort/**', '**/public/vad/**'],
      },
    },
    assetsInclude: ['**/*.moc3'],
  };
});
