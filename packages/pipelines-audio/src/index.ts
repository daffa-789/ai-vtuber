/**
 * `@silverwolf/pipelines-audio` — rantai suara (piper → rvc) di browser.
 *
 * Pengganti `server_py/{jalur_suara,tts_piper,tts_rvc,wav}.py`. Modul di sini
 * diisi bertahap: Fase 3 (piper + chain) lalu Fase 4 (rvc).
 */

export * from './wav.ts'
export * from './rvc/params.ts'
