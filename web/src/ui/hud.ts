import type { CarSpec } from '../sim/types';
import { MIN_STEINS, MAX_STEINS } from '../core/steins';

const $ = <T extends HTMLElement>(root: ParentNode, sel: string): T => {
  const e = root.querySelector(sel);
  if (!e) throw new Error(`HUD element missing: ${sel}`);
  return e as T;
};

export interface HudHandlers {
  prev(): void; next(): void; add(): void; remove(): void; go(): void; mute(): void;
}

/** All DOM UI. Owns no game state: callers push values in, and receive button callbacks. */
export class Hud {
  private root: HTMLElement;
  private el: Record<string, HTMLElement> = {};
  private noticeTimer = 0;
  private toastTimer = 0;
  readonly touch: HTMLElement;
  readonly isTouch: boolean;

  constructor(root: HTMLElement, h: HudHandlers) {
    this.root = root;
    root.innerHTML = `
<div id="loading"><div><div class="mark">GTLinks</div><div class="sub">Setting up the terrace&hellip;</div><div class="bar"><i></i></div><div class="sub" id="loadmsg" style="font-size:12px"></div></div></div>
<div id="fail" class="hidden"><div><h2>Can't start the game</h2><p id="failmsg"></p><p style="opacity:.7;font-size:13px">GTLinks needs WebGPU or WebGL2. Try an up-to-date Chrome, Edge, Firefox or Safari, and check hardware acceleration is on.</p></div></div>
<div id="brand"><span class="wordmark">GTLinks</span><small>Nine holes. Fifteen steins. One car.</small></div>
<div id="topright"><span id="backend" title="Active renderer backend">&hellip;</span><button id="mute" aria-label="Mute audio" title="Mute (M)">&#128266;</button></div>
<section id="lodge" class="hidden">
  <button class="arrow hit" id="prev" aria-label="Previous car">&#8249;</button><button class="arrow hit" id="next" aria-label="Next car">&#8250;</button>
  <div id="card" class="panel"><h2 id="cname"></h2><p id="cchar"></p>
    <div class="stat"><span>Stability</span><b><i id="s1"></i></b></div><div class="stat"><span>Agility</span><b><i id="s2"></i></b></div><div class="stat"><span>Presence</span><b><i id="s3"></i></b></div><div id="dots"></div></div>
  <div id="dock"><div id="help"></div>
    <div id="dockrow" class="panel"><button class="step" id="rem" aria-label="Take a stein off the car">&minus;</button>
      <div id="count" aria-live="polite"><strong>0</strong><span> / ${MAX_STEINS}</span><small>steins loaded</small></div>
      <button class="step" id="add" aria-label="Put a stein on the car">+</button>
      <div id="sever"><small>Steering</small><b><i></i></b></div>
      <button id="go" disabled>GO</button></div></div>
  <div id="toast"></div>
</section>
<section id="drive" class="hidden">
  <div id="holeinfo" class="panel"><strong>Hole 1 / 9</strong><small>Par 4</small></div>
  <div id="steinhud" class="panel">&#127866; <b>0</b> steins</div>
  <div id="callouts"></div><div id="notice"></div>
  <div id="speed"><strong>0</strong><span>MPH</span></div>
  <div id="wheel" class="panel"><small>applied vs input</small><div class="track"><span class="in"></span><span class="out"></span></div></div>
</section>
<section id="wreck" class="hidden"><div id="cam">Drone cam</div>
  <div id="lower"><div class="tag">REPLAY</div><div class="body"><div class="name"></div><div class="meta"></div></div></div></section>
<div id="touch" class="hidden"><div id="stick"><i></i></div><button class="pedal" id="gas">GAS</button><button class="pedal" id="brk">BRAKE</button><button id="hbk">HAND<br>BRAKE</button></div>
<div id="fade" class="on"></div>`;
    const ids = ['loading', 'fail', 'failmsg', 'loadmsg', 'backend', 'mute', 'lodge', 'drive', 'wreck', 'prev', 'next', 'cname', 'cchar', 's1', 's2', 's3', 'dots', 'help', 'count', 'add', 'rem', 'sever', 'go', 'toast', 'holeinfo', 'steinhud', 'callouts', 'notice', 'speed', 'wheel', 'lower', 'fade', 'touch', 'stick', 'gas', 'brk', 'hbk'];
    for (const id of ids) this.el[id] = $(root, `#${id}`);
    this.touch = this.el.touch;
    this.isTouch = matchMedia('(pointer: coarse)').matches || 'ontouchstart' in window || new URLSearchParams(location.search).has('touch');
    this.el.prev.onclick = () => h.prev();
    this.el.next.onclick = () => h.next();
    this.el.add.onclick = () => h.add();
    this.el.rem.onclick = () => h.remove();
    (this.el.go as HTMLButtonElement).onclick = () => h.go();
    this.el.mute.onclick = () => h.mute();
    this.el.help.innerHTML = `Drag steins from the table onto the car. <b>${MIN_STEINS}</b> to start, up to <b>${MAX_STEINS}</b>. Every stein past ten makes the steering worse.`;
  }

  // -------- generic
  setBackend(label: string): void { this.el.backend.textContent = label; }
  setMuted(m: boolean): void { this.el.mute.innerHTML = m ? '&#128263;' : '&#128266;'; this.el.mute.setAttribute('aria-pressed', String(m)); }
  loadProgress(frac: number, msg: string): void { (this.el.loading.querySelector('.bar i') as HTMLElement).style.width = `${Math.round(frac * 100)}%`; this.el.loadmsg.textContent = msg; }
  hideLoading(): void { this.el.loading.classList.add('hidden'); }
  fail(msg: string): void { this.el.loading.classList.add('hidden'); this.el.failmsg.textContent = msg; this.el.fail.classList.remove('hidden'); }
  fade(on: boolean, quick = false): void { this.el.fade.classList.toggle('quick', quick); this.el.fade.classList.toggle('on', on); }
  get fadeEl(): HTMLElement { return this.el.fade; }

  /** Show exactly one of the three in-game screens. */
  screen(s: 'lodge' | 'drive' | 'wreck' | 'none'): void {
    this.el.lodge.classList.toggle('hidden', s !== 'lodge');
    this.el.drive.classList.toggle('hidden', s !== 'drive');
    this.el.wreck.classList.toggle('hidden', s !== 'wreck');
    this.el.touch.classList.toggle('hidden', !(this.isTouch && s === 'drive'));
    if (s !== 'wreck') this.el.lower.classList.remove('on');
    $(this.root, '#brand').classList.toggle('hidden', s === 'wreck');
  }

  // -------- lodge
  setCar(spec: CarSpec, stats: { stability: number; agility: number; presence: number }, index: number, total: number): void {
    this.el.cname.textContent = spec.name;
    this.el.cchar.textContent = spec.character;
    (this.el.s1.style as CSSStyleDeclaration).width = `${Math.round(stats.stability * 100)}%`;
    (this.el.s2.style as CSSStyleDeclaration).width = `${Math.round(stats.agility * 100)}%`;
    (this.el.s3.style as CSSStyleDeclaration).width = `${Math.round(stats.presence * 100)}%`;
    this.el.dots.innerHTML = Array.from({ length: total }, (_, i) => `<i class="${i === index ? 'on' : ''}"></i>`).join('');
  }
  setCount(n: number, canGo: boolean, severity: number): void {
    this.el.count.innerHTML = `<strong>${n}</strong><span> / ${MAX_STEINS}</span><small>steins loaded</small>`;
    (this.el.add as HTMLButtonElement).disabled = n >= MAX_STEINS;
    (this.el.rem as HTMLButtonElement).disabled = n <= 0;
    const go = this.el.go as HTMLButtonElement;
    go.disabled = !canGo;
    go.innerHTML = canGo ? `GO<small>${n === MAX_STEINS ? 'barely steerable' : 'more steins, worse steering'}</small>` : `Need ${MIN_STEINS - n} more`;
    (this.el.sever.querySelector('i') as HTMLElement).style.width = `${Math.round((canGo ? 0.12 + 0.88 * severity : 0.05) * 100)}%`;
    this.el.sever.querySelector('small')!.textContent = canGo ? (severity < 0.34 ? 'Steering: sloppy' : severity < 0.75 ? 'Steering: dreadful' : 'Steering: hopeless') : 'Steering: sober?';
  }
  toast(msg: string): void {
    const t = this.el.toast;
    t.textContent = msg; t.classList.add('on');
    clearTimeout(this.toastTimer);
    this.toastTimer = window.setTimeout(() => t.classList.remove('on'), 1800);
  }

  // -------- driving
  drive(o: { mph: number; hole: number; par: number; steins: number; applied: number; input: number }): void {
    this.el.speed.firstElementChild!.textContent = String(Math.max(0, Math.round(o.mph)));
    this.el.holeinfo.innerHTML = `<strong>Hole ${o.hole + 1} / 9</strong><small>Par ${o.par}</small>`;
    this.el.steinhud.innerHTML = `&#127866; <b>${o.steins}</b> steins`;
    const pos = (v: number) => `${50 + Math.max(-1, Math.min(1, -v)) * 46}%`; // left (+1) is shown on the left
    ($(this.el.wheel, '.in')).style.left = pos(o.input);
    ($(this.el.wheel, '.out')).style.left = pos(o.applied);
  }
  callout(text: string, points: number): void {
    const d = document.createElement('div');
    d.className = 'call';
    d.textContent = text;
    if (points > 0) { const s = document.createElement('small'); s.textContent = `+${Math.round(points)}`; d.appendChild(s); }
    this.el.callouts.appendChild(d);
    while (this.el.callouts.children.length > 3) this.el.callouts.firstElementChild!.remove();
    setTimeout(() => d.remove(), 1950);
  }
  notice(big: string, small: string): void {
    const n = this.el.notice;
    n.innerHTML = '';
    n.append(big);
    const s = document.createElement('small'); s.textContent = small; n.appendChild(s);
    n.classList.remove('on'); void n.offsetWidth; n.classList.add('on');
    clearTimeout(this.noticeTimer);
    this.noticeTimer = window.setTimeout(() => n.classList.remove('on'), 3300);
  }
  hiccup(x: number, y: number): void {
    const d = document.createElement('div');
    d.className = 'hic'; d.textContent = 'hic!';
    d.style.left = `${x}px`; d.style.top = `${y}px`;
    this.el.drive.appendChild(d);
    setTimeout(() => d.remove(), 1150);
  }
  clearTransient(): void { this.el.callouts.innerHTML = ''; this.el.notice.classList.remove('on'); this.el.drive.querySelectorAll('.hic').forEach((e) => e.remove()); }

  // -------- wreck
  lowerThird(name: string, steins: number, score: number): void {
    this.el.lower.querySelector('.name')!.textContent = name;
    const m = this.el.lower.querySelector('.meta') as HTMLElement;
    m.innerHTML = '';
    const a = document.createElement('span'); a.append('Steins ', Object.assign(document.createElement('b'), { textContent: String(steins) }));
    const b = document.createElement('span'); b.append('  ·  Trick score ', Object.assign(document.createElement('b'), { textContent: String(Math.round(score)) }));
    m.append(a, b);
    this.el.lower.classList.add('on');
  }
  hideLower(): void { this.el.lower.classList.remove('on'); }

  /** Touch handles for the input module. */
  get touchEls(): { stick: HTMLElement; gas: HTMLElement; brk: HTMLElement; hbk: HTMLElement } {
    return { stick: this.el.stick, gas: this.el.gas, brk: this.el.brk, hbk: this.el.hbk };
  }
}
