/** Web Audio synthesis only: no audio files. Engine, tyres, thumps, gasp, hiccup, clinks. */
export class AudioEngine {
  private ctx: AudioContext | null = null;
  private master!: GainNode;
  private engineGain!: GainNode; private osc1!: OscillatorNode; private osc2!: OscillatorNode; private sub!: OscillatorNode; private engineLp!: BiquadFilterNode;
  private tyreGain!: GainNode; private tyreBp!: BiquadFilterNode;
  private noiseBuf!: AudioBuffer;
  private _muted = false;
  private surface = 0;
  private engineOn = false;

  constructor() {
    try { this._muted = localStorage.getItem('gtlinks.muted') === '1'; } catch { /* storage may be blocked */ }
  }

  get muted(): boolean { return this._muted; }

  /** Create or resume the context. Must be called from a user gesture. */
  unlock(): void {
    if (!this.ctx) {
      const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AC) return;
      this.ctx = new AC();
      this.build();
    }
    if (this.ctx.state === 'suspended') void this.ctx.resume();
  }

  private build(): void {
    const c = this.ctx!;
    this.master = c.createGain();
    this.master.gain.value = this._muted ? 0 : 0.8;
    const comp = c.createDynamicsCompressor();
    this.master.connect(comp).connect(c.destination);
    // noise source shared by tyres, gasp and foam
    const len = c.sampleRate * 2;
    this.noiseBuf = c.createBuffer(1, len, c.sampleRate);
    const d = this.noiseBuf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    // engine: two detuned saws and a sub through a low-pass
    this.engineGain = c.createGain(); this.engineGain.gain.value = 0;
    this.engineLp = c.createBiquadFilter(); this.engineLp.type = 'lowpass'; this.engineLp.frequency.value = 600; this.engineLp.Q.value = 2;
    this.osc1 = c.createOscillator(); this.osc1.type = 'sawtooth';
    this.osc2 = c.createOscillator(); this.osc2.type = 'square';
    this.sub = c.createOscillator(); this.sub.type = 'sine';
    const g2 = c.createGain(); g2.gain.value = 0.35; const g3 = c.createGain(); g3.gain.value = 0.7;
    this.osc1.connect(this.engineLp); this.osc2.connect(g2).connect(this.engineLp); this.sub.connect(g3).connect(this.engineLp);
    this.engineLp.connect(this.engineGain).connect(this.master);
    this.osc1.start(); this.osc2.start(); this.sub.start();
    // tyres and surface
    const n = c.createBufferSource(); n.buffer = this.noiseBuf; n.loop = true;
    this.tyreBp = c.createBiquadFilter(); this.tyreBp.type = 'bandpass'; this.tyreBp.frequency.value = 900; this.tyreBp.Q.value = 0.8;
    this.tyreGain = c.createGain(); this.tyreGain.gain.value = 0;
    n.connect(this.tyreBp).connect(this.tyreGain).connect(this.master);
    n.start();
    this.engineOn = true;
  }

  toggleMute(): boolean {
    this._muted = !this._muted;
    try { localStorage.setItem('gtlinks.muted', this._muted ? '1' : '0'); } catch { /* ignore */ }
    if (this.ctx) this.master.gain.setTargetAtTime(this._muted ? 0 : 0.8, this.ctx.currentTime, 0.03);
    return this._muted;
  }

  setSurface(id: number): void { this.surface = id; }

  /** Continuous engine and tyre voices. `active` is false in menus. */
  drive(active: boolean, speed: number, throttle: number, wheelsOnGround: number, slip: number): void {
    if (!this.ctx || !this.engineOn) return;
    const t = this.ctx.currentTime;
    const v = Math.abs(speed);
    const rpm = 0.5 + Math.min(1, (v % 14) / 14) * 0.25 + Math.min(1, v / 60) * 0.55 + throttle * 0.25;
    const f = 38 + rpm * 62;
    this.osc1.frequency.setTargetAtTime(f, t, 0.05);
    this.osc2.frequency.setTargetAtTime(f * 1.005, t, 0.05);
    this.sub.frequency.setTargetAtTime(f * 0.5, t, 0.05);
    this.engineLp.frequency.setTargetAtTime(260 + throttle * 700 + v * 9, t, 0.08);
    this.engineGain.gain.setTargetAtTime(active ? 0.06 + throttle * 0.07 : 0.0, t, 0.1);
    const onGround = wheelsOnGround / 4;
    const base = this.surface === 3 ? 0.32 : this.surface === 1 || this.surface === 2 ? 0.16 : this.surface === 5 ? 0.24 : 0.22;
    this.tyreGain.gain.setTargetAtTime(active ? Math.min(0.28, (v / 50) * base * onGround + slip * 0.1) : 0, t, 0.06);
    this.tyreBp.frequency.setTargetAtTime((this.surface === 3 ? 1400 : this.surface === 1 || this.surface === 2 ? 3200 : 1800) + v * 25, t, 0.1);
  }

  private noiseShot(freq: number, q: number, dur: number, gain: number, type: BiquadFilterType = 'bandpass', sweepTo?: number, delay = 0): void {
    const c = this.ctx; if (!c) return;
    const t = c.currentTime + delay;
    const s = c.createBufferSource(); s.buffer = this.noiseBuf;
    const f = c.createBiquadFilter(); f.type = type; f.frequency.setValueAtTime(freq, t); f.Q.value = q;
    if (sweepTo) f.frequency.exponentialRampToValueAtTime(sweepTo, t + dur);
    const g = c.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(gain, t + Math.min(0.03, dur * 0.2)); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(f).connect(g).connect(this.master);
    s.start(t, Math.random(), dur + 0.05);
  }
  private tone(f0: number, f1: number, dur: number, gain: number, type: OscillatorType = 'sine', delay = 0): void {
    const c = this.ctx; if (!c) return;
    const t = c.currentTime + delay;
    const o = c.createOscillator(); o.type = type; o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(Math.max(1, f1), t + dur);
    const g = c.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(gain, t + 0.008); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g).connect(this.master);
    o.start(t); o.stop(t + dur + 0.05);
  }

  thump(strength: number): void {
    const s = Math.max(0.15, Math.min(1, strength));
    this.tone(120, 38, 0.32, 0.5 * s, 'sine');
    this.noiseShot(500, 0.7, 0.25, 0.4 * s, 'lowpass');
    if (s > 0.5) this.noiseShot(2400, 1, 0.12, 0.2 * s, 'bandpass', 800);
  }
  gasp(): void { this.noiseShot(500, 1.6, 0.5, 0.2, 'bandpass', 1500); this.noiseShot(900, 2, 0.35, 0.14, 'bandpass', 2000, 0.28); }
  hiccup(): void { this.tone(300, 170, 0.14, 0.2, 'triangle'); this.tone(560, 330, 0.08, 0.1, 'sine', 0.01); }
  clink(strength = 0.5): void {
    const g = 0.05 + strength * 0.07;
    this.tone(2650 + Math.random() * 300, 2600, 0.22, g, 'sine');
    this.tone(3980 + Math.random() * 400, 3900, 0.15, g * 0.7, 'sine', 0.004);
    this.tone(1790, 1760, 0.28, g * 0.5, 'sine', 0.002);
  }
  splash(): void { this.noiseShot(3500, 0.9, 0.35, 0.16, 'highpass'); this.tone(500, 260, 0.1, 0.05, 'sine'); }
  chime(): void { this.tone(660, 660, 0.25, 0.1, 'triangle'); this.tone(880, 880, 0.3, 0.1, 'triangle', 0.1); }
  /** Low rumble for the car getting away. */
  alarm(): void { this.tone(220, 330, 0.25, 0.12, 'square'); this.tone(220, 330, 0.25, 0.12, 'square', 0.3); }
  silence(): void { if (this.ctx && this.engineOn) { this.engineGain.gain.setTargetAtTime(0, this.ctx.currentTime, 0.1); this.tyreGain.gain.setTargetAtTime(0, this.ctx.currentTime, 0.1); } }
}
