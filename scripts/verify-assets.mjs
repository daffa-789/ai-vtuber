import { existsSync, statSync } from 'node:fs'
import { resolve } from 'node:path'
const root = process.cwd()
const required = [
  ['Piper model', 'assets/piper/id_ID-news_tts-medium.onnx'],
  ['Piper config', 'assets/piper/id_ID-news_tts-medium.onnx.json'],
  ['ContentVec RVC v2', 'assets/encoders/vec-768-layer-12.onnx'],
  ['RVC voice', 'assets/voices/silverwolf/model.onnx'],
  ['Live2D model', 'assets/live2d/silverwolf/silverwolf.model3.json'],
  ['Cubism Core', 'assets/live2d/live2dcubismcore.min.js'],
]
let missing = 0
for (const [label, path] of required) {
  const full = resolve(root, path), ok = existsSync(full) && statSync(full).size > 0
  console.log(`${ok ? '✓' : '✗'} ${label}: ${path}`); if (!ok) missing++
}
if (missing) { console.error(`\n${missing} aset belum ada. App tetap dapat dibuka, tetapi fitur terkait memakai fallback.`); process.exitCode = 1 }
