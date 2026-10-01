import { join } from 'node:path'
import type { Server } from 'node:http'
import type { Konfig } from '@silverwolf/core-config'
import { CharacterVault, bacaPersona } from '@silverwolf/core-character'
import { CharacterAgent } from '@silverwolf/core-agent'
import { createApiServer } from './http.ts'
import { LlamaServerProcess, cariModel } from './llama-process.ts'
import { OpenAiCompatibleProvider, StubLlmProvider } from './providers.ts'

const PERSONA_CADANGAN = 'Kamu adalah Silver Wolf, hacker Punklorde dari Stellaron Hunters. Kamu memanggil pengguna Master, bicara santai, ringkas, dan tidak memakai emoji.'
export interface RuntimeOptions { staticRoot?: string; assetRoot?: string; vaultRoot?: string }
export interface SilverWolfRuntime { server: Server; modelName: string; vault: CharacterVault; close(): Promise<void> }
export async function createSilverWolfRuntime(config: Konfig, options: RuntimeOptions = {}): Promise<SilverWolfRuntime> {
  let persona = PERSONA_CADANGAN
  try { persona = await bacaPersona(config.akarPersona) } catch (error) { console.warn(`! ${error instanceof Error ? error.message : error}; memakai persona cadangan minimal`) }
  const vault = new CharacterVault(options.vaultRoot ?? join(config.akar, 'silver_wolf_memory'))
  let llama: LlamaServerProcess | undefined
  let provider: OpenAiCompatibleProvider | StubLlmProvider
  let modelName: string
  if (config.stub) { provider = new StubLlmProvider(); modelName = 'stub' }
  else if (config.llmProvider === 'ollama') { provider = new OpenAiCompatibleProvider({ id: 'ollama', baseUrl: config.ollamaUrl, model: config.ollamaModel }); modelName = `ollama/${config.ollamaModel}` }
  else {
    const inferencePort = config.port === 0 ? 18788 : config.port + 1
    llama = new LlamaServerProcess(config, inferencePort); const started = await llama.start(); if (!started.ok) console.warn(`! inferensi lokal belum siap: ${started.reason}`)
    provider = new OpenAiCompatibleProvider({ id: 'llama-server', baseUrl: `http://127.0.0.1:${inferencePort}`, model: cariModel(config) ?? 'gguf' })
    modelName = `${config.llmProvider === 'vulkan' ? 'vulkan' : 'local'}/${cariModel(config)?.split(/[\\/]/).pop() ?? 'belum-ada-model'}`
  }
  const agent = new CharacterAgent({ provider, persona, vault, localPrompt: config.llmProvider !== 'ollama', onError: e => console.error('memori:', e) })
  const server = createApiServer({ config, agent, provider, vault, modelName, staticRoot: options.staticRoot, assetRoot: options.assetRoot ?? join(config.akar, 'assets') })
  return { server, modelName, vault, close: async () => { server.close(); await agent.dispose(); await llama?.stop() } }
}
