import { spawn, type ChildProcess } from 'node:child_process'
import { existsSync, readdirSync, statSync } from 'node:fs'
import { basename, join, resolve } from 'node:path'
import type { Konfig } from '@silverwolf/core-config'

function cari(root: string, cocok: (name: string) => boolean, depth = 3): string | undefined {
  if (!existsSync(root)) return undefined
  if (statSync(root).isFile()) return cocok(basename(root)) ? root : undefined
  for (const item of readdirSync(root, { withFileTypes: true })) {
    const path = join(root, item.name)
    if (item.isFile() && cocok(item.name)) return path
    if (item.isDirectory() && depth > 0) { const found = cari(path, cocok, depth - 1); if (found) return found }
  }
  return undefined
}

export function cariModel(config: Konfig): string | undefined {
  const explicit = resolve(config.akar, config.localModelPath)
  if (config.localModelPath && existsSync(explicit) && statSync(explicit).isFile()) return explicit
  return cari(join(config.akar, 'model'), name => name.toLowerCase().endsWith('.gguf'), 2)
    ?? cari(join(config.akar, 'assets', 'llm'), name => name.toLowerCase().endsWith('.gguf'), 2)
}

export function cariLlamaServer(config: Konfig): string | undefined {
  const root = resolve(config.akar, config.llamaServer)
  const nama = process.platform === 'win32' ? /^llama-server\.exe$/i : /^llama-server$/i
  return cari(root, name => nama.test(name), 3)
}

export class LlamaServerProcess {
  private child?: ChildProcess
  constructor(private readonly config: Konfig, readonly port: number) {}
  async start(): Promise<{ ok: boolean; reason: string }> {
    const binary = cariLlamaServer(this.config), model = cariModel(this.config)
    if (!binary) return { ok: false, reason: `llama-server tidak ditemukan di ${this.config.llamaServer}` }
    if (!model) return { ok: false, reason: 'model GGUF tidak ditemukan' }
    const vulkan = this.config.llmProvider === 'vulkan'
    const args = ['-m', model, '--host', '127.0.0.1', '--port', String(this.port), '-c', String(vulkan ? this.config.vulkanCtx : this.config.localModelCtx), '-t', String(this.config.localModelThreads), '-ngl', String(vulkan ? this.config.vulkanNgl : 0)]
    if (vulkan && this.config.vulkanFa) args.push('--flash-attn', 'on')
    this.child = spawn(binary, args, { cwd: this.config.akar, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true })
    this.child.stdout?.on('data', data => process.stdout.write(`[llama] ${String(data)}`))
    this.child.stderr?.on('data', data => process.stderr.write(`[llama] ${String(data)}`))
    let reason = 'waktu tunggu llama-server habis'
    for (let i = 0; i < 120; i++) {
      if (this.child.exitCode !== null) return { ok: false, reason: `llama-server berhenti (kode ${this.child.exitCode})` }
      try { const r = await fetch(`http://127.0.0.1:${this.port}/health`); if (r.ok) return { ok: true, reason: 'siap' }; reason = `health HTTP ${r.status}` } catch {}
      await new Promise(resolve => setTimeout(resolve, 250))
    }
    await this.stop(); return { ok: false, reason }
  }
  async stop(): Promise<void> {
    const child = this.child; this.child = undefined
    if (!child || child.exitCode !== null) return
    child.kill('SIGTERM')
    await Promise.race([new Promise<void>(resolve => child.once('exit', () => resolve())), new Promise(resolve => setTimeout(resolve, 1500))])
    if (child.exitCode === null) child.kill('SIGKILL')
  }
}
