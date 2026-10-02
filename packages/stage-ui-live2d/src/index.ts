import { Application, Ticker } from 'pixi.js'
import type { StageRenderer } from '@silverwolf/provider-inference'
import { Live2DModel } from 'pixi-live2d-display/cubism4'
import { bacaPanggung, hitungSkala, type PanggungOptions } from './panggung.ts'

export { bacaPanggung, hitungSkala, type PanggungOptions }

export class Live2DRenderer implements StageRenderer {
  private readonly app: Application
  private readonly opsi: PanggungOptions
  private readonly pas: () => void
  private model?: InstanceType<typeof Live2DModel>

  constructor(canvas: HTMLCanvasElement, opsi: Partial<PanggungOptions> = {}) {
    this.opsi = { ...bacaPanggung(), ...opsi }
    Live2DModel.registerTicker(Ticker)
    // "auto" = ikuti devicePixelRatio, dijepit VITE_RENDER_SKALA_MAKS.
    const resolution = Math.min(globalThis.devicePixelRatio || 1, this.opsi.skalaMaks)
    this.app = new Application({
      view: canvas,
      resizeTo: canvas.parentElement ?? window,
      backgroundAlpha: 0,
      antialias: true,
      autoDensity: true,
      resolution,
    })
    // PENTING: `fit` lama hanya dipasang di window.resize, padahal `resizeTo`
    // PIXI juga mengubah ukuran kanvas karena layout (bukan karena jendela).
    // Tanpa baris ini karakter memakai skala basi sampai jendela benar-benar
    // di-resize -- salah satu penyebab "zoom kebesaran".
    this.pas = () => this.paskan()
    this.app.renderer.on('resize', this.pas)
    window.addEventListener('resize', this.pas)
  }

  async load(url: string): Promise<void> {
    const model = await Live2DModel.from(url, { autoInteract: false })
    this.model = model
    this.app.stage.addChild(model)
    this.paskan()
  }

  /**
   * Hitung skala karakter.
   *
   * KUNCI PERBAIKAN: ukuran dasar diambil dari `internalModel`, BUKAN
   * `model.width`. Getter `width` PIXI v6 adalah `scale.x * getLocalBounds().width`
   * -- artinya nilainya ikut berubah oleh skala yang sedang kita hitung, sehingga
   * `fit()` versi lama tidak idempoten: s1 = K (pas), s2 = K/s1 = 1 (ukuran
   * native model, jauh lebih besar dari jendela), s3 = K, dan seterusnya.
   * `internalModel.width` adalah `originalWidth * localTransform.a`, tetap
   * terhadap `model.scale`, jadi aman dipanggil berulang kali.
   */
  private paskan(): void {
    const model = this.model
    if (!model) return
    const dasar = model.internalModel
    if (!dasar?.width || !dasar?.height) return
    const { width: W, height: H } = this.app.screen
    if (!W || !H) return
    const scale = hitungSkala(W, H, dasar.width, dasar.height, this.opsi.zoom)
    if (!scale) return
    model.scale.set(scale)
    // anchor menggeser pivot, sehingga posisi cukup berupa titik jangkar —
    // tidak perlu mengurangi ukuran model seperti versi lama.
    model.anchor.set(this.opsi.x, this.opsi.jangkar)
    model.x = W * this.opsi.x
    model.y = H * this.opsi.jangkar
  }

  setExpression(name: string): void { void this.model?.expression(name) }
  setPose(_name: string, _on: boolean): void {}
  async startMotion(group: string, index: number, priority = 2): Promise<boolean> { return Boolean(await this.model?.motion(group, index, priority)) }
  setMouth(level: number): void {
    const core = this.model?.internalModel.coreModel as { setParameterValueById?: (id: string, value: number) => void } | undefined
    core?.setParameterValueById?.('ParamMouthOpenY', Math.max(0, Math.min(1, level)))
  }
  destroy(): void {
    window.removeEventListener('resize', this.pas)
    this.app.renderer.off('resize', this.pas)
    this.model?.destroy()
    this.app.destroy(false, { children: true, texture: true, baseTexture: true })
  }
}
