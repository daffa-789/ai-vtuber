import { defineConfig } from 'vitest/config'

/**
 * Satu konfigurasi di root. Lingkungan default `node`; uji yang butuh DOM
 * menandai dirinya sendiri dengan docblock `// @vitest-environment happy-dom`
 * di baris pertama berkas. Tiap paket memanggil vitest dengan filter path
 * paketnya (lihat `scripts.test` di package.json masing-masing), sehingga
 * turbo tidak menjalankan seluruh suite berulang kali.
 */
export default defineConfig({
  test: {
    environment: 'node',
    include: [
      'packages/*/test/**/*.spec.ts',
      'apps/*/test/**/*.spec.ts',
    ],
    exclude: ['**/node_modules/**', '**/dist/**', '**/out/**', '**/e2e/**'],
  },
})
