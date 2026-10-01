import { join } from 'node:path'
import { bacaKonfig, konfig as cachedConfig, type Konfig } from '@silverwolf/core-config'
import { CharacterVault, bacaPersona } from '@silverwolf/core-character'
import { CharacterAgent } from '@silverwolf/core-agent'
import { LlamaServerProcess, OpenAiCompatibleProvider, StubLlmProvider, cariModel, createApiServer, listen } from '@silverwolf/server-runtime'

const PERSONA_CADANGAN = `Kamu adalah Silver Wolf, hacker Punklorde dari Stellaron Hunters. Kamu memanggil pengguna Master, bicara santai, ringkas, dan tidak memakai emoji.`

export async function main(config: Konfig = cachedConfig()): Promise<void> {
  let persona = PERSONA_CADANGAN
  try { persona = await bacaPersona(config.akarPersona) }
  catch (error) { console.warn(`! ${error instanceof Error ? error.message : error}; memakai persona cadangan minimal`) }

  const vaultRoot = join(config.akar, 'silver_wolf_memory')
  const vault = new CharacterVault(vaultRoot)
  let llama: LlamaServerProcess | undefined
  let provider: OpenAiCompatibleProvider | StubLlmProvider
  let modelName: string

  if (config.stub) {
    provider = new StubLlmProvider(); modelName = 'stub'
  } else if (config.llmProvider === 'ollama') {
    provider = new OpenAiCompatibleProvider({ id: 'ollama', baseUrl: config.ollamaUrl, model: config.ollamaModel })
    modelName = `ollama/${config.ollamaModel}`
  } else {
    const inferencePort = config.port === 0 ? 18788 : config.port + 1
    llama = new LlamaServerProcess(config, inferencePort)
    const started = await llama.start()
    if (!started.ok) console.warn(`! inferensi lokal belum siap: ${started.reason}`)
    provider = new OpenAiCompatibleProvider({ id: 'llama-server', baseUrl: `http://127.0.0.1:${inferencePort}`, model: cariModel(config) ?? 'gguf' })
    modelName = `${config.llmProvider === 'vulkan' ? 'vulkan' : 'local'}/${cariModel(config)?.split(/[\\/]/).pop() ?? 'belum-ada-model'}`
  }

  const agent = new CharacterAgent({ provider, persona, vault, localPrompt: config.llmProvider !== 'ollama', onError: e => console.error('memori:', e) })
  const server = createApiServer({ config, agent, provider, vault, modelName })
  const port = await listen(server, config.port)
  console.log(`Silver Wolf sidecar Node siap di http://0.0.0.0:${port}`)
  console.log(`  model: ${modelName} · memori: ${vault.available() ? 'siap' : vault.unavailableReason()}`)
  for (const warning of config.warnings) console.warn(`  ! ${warning}`)

  let closing = false
  const close = async () => {
    if (closing) return; closing = true
    server.close(); await agent.dispose(); await llama?.stop()
  }
  process.once('SIGINT', () => void close().finally(() => process.exit(0)))
  process.once('SIGTERM', () => void close().finally(() => process.exit(0)))
}

if (import.meta.url === new URL(process.argv[1] ?? '', 'file:').href)
  void main().catch(error => { console.error(error); process.exitCode = 1 })

export { bacaKonfig }
