import { app, BrowserWindow, globalShortcut, Menu, nativeImage, shell, Tray } from 'electron'
import { spawn, type ChildProcess } from 'node:child_process'
import { existsSync, mkdirSync, readdirSync } from 'node:fs'
import { join, resolve } from 'node:path'

/**
 * Proses utama aplikasi desktop Silver Wolf.
 *
 * Tugasnya sengaja dibuat tipis: menjalankan sidecar Go (`bin/silverwolf-sidecar.exe`),
 * membaca port yang dilaporkannya, lalu menampilkan renderer di jendela native.
 * Semua logika percakapan, memori, dan inferensi hidup di sidecar Go.
 */

let window: BrowserWindow | undefined, tray: Tray | undefined, sidecar: ChildProcess | undefined
let quitting = false
const repoRoot = resolve(__dirname, '../..')

function iconPath(): string { return app.isPackaged ? join(process.resourcesPath, 'icon.png') : resolve(__dirname, '../../resources/icon.png') }

/** Lokasi binary sidecar Go: ikut installer di `resources/bin`, atau hasil build di akar repo. */
function sidecarPath(): string {
  return app.isPackaged
    ? join(process.resourcesPath, 'bin', 'silverwolf-sidecar.exe')
    : join(repoRoot, 'bin', 'silverwolf-sidecar.exe')
}

/** Ada model GGUF di folder `model/`? Dipakai untuk menentukan mode tiruan. */
function adaModelGguf(root: string): boolean {
  const jelajah = (dir: string, kedalaman: number): boolean => {
    if (!existsSync(dir)) return false
    for (const item of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, item.name)
      if (item.isFile() && item.name.toLowerCase().endsWith('.gguf')) return true
      if (item.isDirectory() && kedalaman > 0 && jelajah(path, kedalaman - 1)) return true
    }
    return false
  }
  return jelajah(join(root, 'model'), 2) || jelajah(join(root, 'assets', 'llm'), 2)
}

/**
 * Jalankan sidecar Go dan tunggu sampai ia melaporkan port-nya.
 *
 * Port dipilih acak (`-port 0`) supaya tidak bertabrakan dengan sidecar yang
 * mungkin sudah berjalan; sidecar mencetak `port=<angka>` yang kita tangkap
 * di sini, bukan ditebak dari log.
 */
function jalankanSidecar(argumen: string[], root: string, stub: boolean): Promise<number> {
  return new Promise((beres, gagal) => {
    const binary = sidecarPath()
    if (!existsSync(binary)) {
      gagal(new Error(`binary sidecar Go belum ada: ${binary}. Jalankan "npm run sidecar:build" lebih dulu.`))
      return
    }
    const anak = spawn(binary, argumen, {
      cwd: root,
      windowsHide: true,
      // Mode tiruan dipakai saat belum ada model: UI tetap hidup dan bisa diuji.
      env: { ...process.env, VTUBER_PORT: '0', ...(stub ? { VTUBER_STUB: 'ya' } : {}) },
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    sidecar = anak
    let penampung = ''
    const selesai = (fn: () => void): void => {
      clearTimeout(waktuHabis)
      anak.stdout?.off('data', saatData)
      fn()
    }
    const saatData = (data: Buffer): void => {
      penampung += data.toString('utf8')
      const baris = penampung.split(/\r?\n/)
      penampung = baris.pop() ?? ''
      for (const mentah of baris) {
        const teks = mentah.trim()
        if (!teks) continue
        console.log(`[sidecar] ${teks}`)
        const cocok = /^port=(\d+)$/.exec(teks)
        if (cocok?.[1]) selesai(() => beres(Number(cocok[1])))
      }
    }
    const waktuHabis = setTimeout(() => selesai(() => gagal(new Error('sidecar Go tidak melaporkan port dalam 60 detik'))), 60_000)
    anak.stdout?.on('data', saatData)
    anak.stderr?.on('data', data => console.error(`[sidecar] ${String(data).trimEnd()}`))
    anak.on('error', error => selesai(() => gagal(error)))
    anak.on('exit', (kode) => {
      console.warn(`[sidecar] berhenti dengan kode ${kode}`)
      selesai(() => gagal(new Error(`sidecar Go berhenti lebih awal (kode ${kode})`)))
    })
  })
}

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
  if (app.isPackaged) for (const folder of ['assets/piper', 'assets/encoders', 'assets/voices/silverwolf', 'assets/live2d/silverwolf', 'model', 'bin/llama', 'silver_wolf_memory']) {
    const path = join(root, folder)
    if (!existsSync(path)) mkdirSync(path, { recursive: true })
  }
  const punyaEnv = existsSync(join(root, '.env'))
  const stub = app.isPackaged && (!punyaEnv || !adaModelGguf(root))

  const rendererUrl = process.env.ELECTRON_RENDERER_URL
  const staticRoot = rendererUrl ? undefined : join(__dirname, '../renderer')
  const argumen = ['-root', root, '-port', '0', '-host', '127.0.0.1',
    '-assets', join(root, 'assets'), '-vault', join(root, 'silver_wolf_memory')]
  if (staticRoot) argumen.push('-static', staticRoot)
  const port = await jalankanSidecar(argumen, root, stub)
  const alamatRenderer = rendererUrl ? new URL(rendererUrl) : undefined
  alamatRenderer?.searchParams.set('api', `http://127.0.0.1:${port}`)
  await createWindow(alamatRenderer?.toString() ?? `http://127.0.0.1:${port}/`)
  installTray()
  globalShortcut.register('CommandOrControl+Shift+S', () => window?.isVisible() ? window.hide() : window?.show())
}
if (!app.requestSingleInstanceLock()) app.quit()
else {
  app.on('second-instance', () => { window?.show(); window?.focus() })
  app.whenReady().then(boot).catch(error => { console.error(error); app.quit() })
  app.on('before-quit', () => { quitting = true })
  app.on('will-quit', () => {
    globalShortcut.unregisterAll()
    // Sidecar ikut mati bersama aplikasi, supaya llama-server tidak tertinggal.
    if (sidecar && sidecar.exitCode === null) sidecar.kill()
  })
  app.on('window-all-closed', () => { /* tetap hidup di tray */ })
}
