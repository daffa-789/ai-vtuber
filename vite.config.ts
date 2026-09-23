import { createReadStream, existsSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { defineConfig, type Plugin } from 'vite';

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

export default defineConfig({
  plugins: [sajikanAsetOrt()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8787', changeOrigin: false },
    },
  },
  assetsInclude: ['**/*.moc3'],
});
