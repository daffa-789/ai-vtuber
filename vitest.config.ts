import { defineConfig } from 'vitest/config'
import { resolve } from 'node:path'

/**
 * Satu konfigurasi di root. Lingkungan default `node`; uji yang butuh DOM
 * menandai dirinya sendiri dengan docblock `// @vitest-environment happy-dom`
 * di baris pertama berkas. Tiap paket memanggil vitest dengan filter path
 * paketnya (lihat `scripts.test` di package.json masing-masing), sehingga
 * turbo tidak menjalankan seluruh suite berulang kali.
 */
export default defineConfig({
  resolve: { alias: {
    '@silverwolf/audio': resolve(__dirname, 'packages/audio/src'),
    '@silverwolf/core-character': resolve(__dirname, 'packages/core-character/src'),
    '@silverwolf/core-config': resolve(__dirname, 'packages/core-config/src'),
    '@silverwolf/pipelines-audio': resolve(__dirname, 'packages/pipelines-audio/src'),
    '@silverwolf/provider-inference': resolve(__dirname, 'packages/provider-inference/src'),
    '@silverwolf/stage-ui': resolve(__dirname, 'packages/stage-ui/src'),
    '@silverwolf/stage-ui-live2d': resolve(__dirname, 'packages/stage-ui-live2d/src'),
  } },
  test: {
    environment: 'node',
    include: [
      'packages/*/test/**/*.spec.ts',
      'apps/*/test/**/*.spec.ts',
    ],
    exclude: ['**/node_modules/**', '**/dist/**', '**/out/**', '**/e2e/**'],
    /**
     * Berkas tes dijalankan BERURUTAN, bukan paralel.
     *
     * Dengan paralel, jumlah tes yang benar-benar jalan berubah-ubah di kode
     * yang sama — terukur 57, lalu 48, lalu 43 pada tiga jalan berturut-turut,
     * dan berkas seperti `core-config`, `wav`, serta `stage-ui-live2d` ada yang
     * hilang tanpa satu pun pesan gagal. Tes yang diam-diam tidak jalan lebih
     * berbahaya daripada tes yang gagal, karena memberi rasa aman palsu.
     * Suite ini kecil (di bawah 5 detik), jadi berurutan tidak terasa.
     */
    fileParallelism: false,
  },
})
