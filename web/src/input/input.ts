import { keyboardIntent, gamepadIntent, mergeIntents, NEUTRAL } from './mapping';
import type { Intent } from './mapping';

export interface TouchEls { stick: HTMLElement; gas: HTMLElement; brk: HTMLElement; hbk: HTMLElement }

/** Collects keyboard, gamepad and on-screen touch into one Intent per frame. */
export class InputManager {
  private down = new Set<string>();
  private touch: Intent = { ...NEUTRAL };
  private cleanup: Array<() => void> = [];
  /** Keys that were pressed this frame and not auto-repeats; consumed by `takePressed`. */
  private pressed: string[] = [];

  constructor(touchEls: TouchEls | null) {
    const kd = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLElement && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(e.code) && !(e.target instanceof HTMLButtonElement)) e.preventDefault();
      if (!e.repeat) this.pressed.push(e.code);
      this.down.add(e.code);
    };
    const ku = (e: KeyboardEvent) => { this.down.delete(e.code); };
    const blur = () => { this.down.clear(); };
    window.addEventListener('keydown', kd);
    window.addEventListener('keyup', ku);
    window.addEventListener('blur', blur);
    this.cleanup.push(() => { window.removeEventListener('keydown', kd); window.removeEventListener('keyup', ku); window.removeEventListener('blur', blur); });
    if (touchEls) this.bindTouch(touchEls);
  }

  private bindTouch(t: TouchEls): void {
    const knob = t.stick.querySelector('i') as HTMLElement;
    let stickId = -1;
    const move = (e: PointerEvent) => {
      const r = t.stick.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const dx = Math.max(-1, Math.min(1, (e.clientX - cx) / (r.width / 2)));
      this.touch.steer = -dx; // dragging right steers right (-1)
      knob.style.transform = `translate(${dx * r.width * 0.28}px, 0)`;
    };
    t.stick.addEventListener('pointerdown', (e) => { stickId = e.pointerId; t.stick.setPointerCapture(e.pointerId); move(e); });
    t.stick.addEventListener('pointermove', (e) => { if (e.pointerId === stickId) move(e); });
    const end = (e: PointerEvent) => { if (e.pointerId === stickId) { stickId = -1; this.touch.steer = 0; knob.style.transform = ''; } };
    t.stick.addEventListener('pointerup', end); t.stick.addEventListener('pointercancel', end);
    const hold = (el: HTMLElement, on: (v: boolean) => void) => {
      el.addEventListener('pointerdown', (e) => { el.setPointerCapture(e.pointerId); el.classList.add('down'); on(true); });
      const up = () => { el.classList.remove('down'); on(false); };
      el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up);
    };
    hold(t.gas, (v) => { this.touch.throttle = v ? 1 : 0; });
    hold(t.brk, (v) => { this.touch.brake = v ? 1 : 0; });
    hold(t.hbk, (v) => { this.touch.handbrake = v; });
  }

  /** Current merged intent. */
  intent(): Intent {
    const list: Intent[] = [keyboardIntent(this.down), this.touch];
    const pads = navigator.getGamepads?.() ?? [];
    for (const p of pads) if (p && p.connected) list.push(gamepadIntent(p.axes, p.buttons));
    return mergeIntents(list);
  }

  /** Key codes pressed since the last call. */
  takePressed(): string[] { const p = this.pressed; this.pressed = []; return p; }
  /** Gamepad button edge for menu use: any of A/Start pressed. */
  padStart(): boolean { const p = (navigator.getGamepads?.() ?? []).find((x) => x && x.connected); return !!p && (p.buttons[9]?.pressed ?? false); }

  dispose(): void { for (const c of this.cleanup) c(); this.cleanup = []; }
}
