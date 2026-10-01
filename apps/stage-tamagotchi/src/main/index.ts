import { app, BrowserWindow, globalShortcut, Menu, nativeImage, shell, Tray } from 'electron'
import { join, resolve } from 'node:path'
import { mkdirSync } from 'node:fs'
import { bacaKonfig, buatEnvSource } from '../../../../packages/core-config/src/index.ts'
import { createSilverWolfRuntime, listen, type SilverWolfRuntime } from '../../../../packages/server-runtime/src/index.ts'

let window: BrowserWindow | undefined, tray: Tray | undefined, runtime: SilverWolfRuntime | undefined
let quitting = false
const repoRoot = resolve(__dirname, '../../../..')

function iconPath(): string { return app.isPackaged ? join(process.resourcesPath, 'icon.png') : resolve(__dirname, '../../resources/icon.png') }
async function createWindow(url: string): Promise<void> {
  window = new BrowserWindow({ width: 1180, height: 760, minWidth: 780, minHeight: 560, show: false, backgroundColor: '#080b12', title: 'Silver Wolf', icon: iconPath(), autoHideMenuBar: true,
    webPreferences: { preload: join(__dirname, '../preload/index.mjs'), contextIsolation: true, sandbox: true, nodeIntegration: false } })
  window.once('ready-to-show', () => window?.show())
  window.on('close', event => { if (!quitting) { event.preventDefault(); window?.hide() } })
  window.webContents.setWindowOpenHandler(({ url: target }) => { if (/^https?:/.test(target)) void shell.openExternal(target); return { action: 'deny' } })
  await window.loadURL(url)
}
function installTray(): void {
  const image = nativeImage.createFromPath(iconPath()).resize({ width: 20, height: 20 })
  tray = new Tray(image); tray.setToolTip('Silver Wolf')
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Tampilkan Silver Wolf', click: () => { window?.show(); window?.focus() } },
    { label: 'Sembunyikan', click: () => window?.hide() },
    { label: 'Buka folder model & konfigurasi', click: () => void shell.openPath(app.getPath('userData')) },
    { type: 'separator' },
    { label: 'Keluar', click: () => { quitting = true; app.quit() } },
  ]))
  tray.on('double-click', () => { window?.show(); window?.focus() })
}
async function boot(): Promise<void> {
  const root = app.isPackaged ? app.getPath('userData') : repoRoot
  if (app.isPackaged) for (const folder of ['assets/piper', 'assets/encoders', 'assets/voices/silverwolf', 'assets/live2d/silverwolf', 'model', 'bin/llama', 'silver_wolf_memory']) mkdirSync(join(root, folder), { recursive: true })
  const source = buatEnvSource(root)
  // Port acak mencegah tabrakan dengan sidecar yang mungkin sudah berjalan.
  source.environ.VTUBER_PORT = '0'
  const config = bacaKonfig(source, root)
  if (app.isPackaged && !source.file.VTUBER_LLM_PROVIDER) config.stub = !Boolean(config.localModelPath)
  const rendererUrl = process.env.ELECTRON_RENDERER_URL
  const staticRoot = rendererUrl ? undefined : join(__dirname, '../renderer')
  runtime = await createSilverWolfRuntime(config, { staticRoot, assetRoot: join(root, 'assets'), vaultRoot: join(root, 'silver_wolf_memory') })
  const port = await listen(runtime.server, 0, '127.0.0.1')
  await createWindow(rendererUrl ?? `http://127.0.0.1:${port}/`)
  installTray()
  globalShortcut.register('CommandOrControl+Shift+S', () => window?.isVisible() ? window.hide() : window?.show())
}
if (!app.requestSingleInstanceLock()) app.quit()
else {
  app.on('second-instance', () => { window?.show(); window?.focus() })
  app.whenReady().then(boot).catch(error => { console.error(error); app.quit() })
  app.on('before-quit', () => { quitting = true })
  app.on('will-quit', () => { globalShortcut.unregisterAll(); void runtime?.close() })
  app.on('window-all-closed', () => { /* tetap hidup di tray */ })
}
