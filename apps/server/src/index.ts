import { konfig as cachedConfig, type Konfig } from '@silverwolf/core-config'
import { createSilverWolfRuntime, listen } from '@silverwolf/server-runtime'

export async function main(config: Konfig = cachedConfig()): Promise<void> {
  const runtime = await createSilverWolfRuntime(config)
  const port = await listen(runtime.server, config.port)
  console.log(`Silver Wolf sidecar Node siap di http://0.0.0.0:${port}`)
  console.log(`  model: ${runtime.modelName} · memori: ${runtime.vault.available() ? 'siap' : runtime.vault.unavailableReason()}`)
  for (const warning of config.warnings) console.warn(`  ! ${warning}`)
  let closing = false
  const close = async () => { if (closing) return; closing = true; await runtime.close() }
  process.once('SIGINT', () => void close().finally(() => process.exit(0)))
  process.once('SIGTERM', () => void close().finally(() => process.exit(0)))
}
if (import.meta.url === new URL(process.argv[1] ?? '', 'file:').href)
  void main().catch(error => { console.error(error); process.exitCode = 1 })
