import { Application } from 'pixi.js'
import type { StageRenderer } from '@silverwolf/provider-inference'
import { Live2DModel } from 'pixi-live2d-display/cubism4'

export class Live2DRenderer implements StageRenderer {
  private readonly app: Application
  private model?: InstanceType<typeof Live2DModel>
  constructor(canvas: HTMLCanvasElement) {
    this.app = new Application({ view: canvas, resizeTo: canvas.parentElement ?? window, backgroundAlpha: 0, antialias: true, autoDensity: true })
  }
  async load(url: string): Promise<void> {
    const model = await Live2DModel.from(url, { autoInteract: false })
    this.model = model; this.app.stage.addChild(model)
    const fit = () => { if (!this.model) return; const scale = Math.min(this.app.screen.width / model.width, this.app.screen.height / model.height) * 0.92; model.scale.set(scale); model.x = (this.app.screen.width - model.width) / 2; model.y = this.app.screen.height - model.height }
    fit(); window.addEventListener('resize', fit)
  }
  setExpression(name: string): void { void this.model?.expression(name) }
  setPose(_name: string, _on: boolean): void {}
  async startMotion(group: string, index: number, priority = 2): Promise<boolean> { return Boolean(await this.model?.motion(group, index, priority)) }
  setMouth(level: number): void {
    const core = this.model?.internalModel.coreModel as { setParameterValueById?: (id: string, value: number) => void } | undefined
    core?.setParameterValueById?.('ParamMouthOpenY', Math.max(0, Math.min(1, level)))
  }
  destroy(): void { this.model?.destroy(); this.app.destroy(false, { children: true, texture: true, baseTexture: true }) }
}
