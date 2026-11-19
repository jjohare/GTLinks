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
  private sirens: { osc: OscillatorNode; gain: GainNode; pan: StereoPannerNode; flip: number; hi: boolean }[] = [];
  private rotorGain: GainNode | null = null; private rotorPan: StereoPannerNode | null = null; private rotorBp: BiquadFilterNode | null = null; private rotorLfo: OscillatorNode | null = null;
  private lastListener = { x: 0, y: 0, z: 0, has: false };

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
    // three European-style two-tone sirens (hi-lo), each through its own pan and distance gain
    for (let i = 0; i < 3; i++) {
      const osc = c.createOscillator(); osc.type = 'sawtooth'; osc.frequency.value = 700;
      const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 2200;
      const gain = c.createGain(); gain.gain.value = 0;
      const pan = c.createStereoPanner();
      osc.connect(lp).connect(gain).connect(pan).connect(this.master);
      osc.start();
      this.sirens.push({ osc, gain, pan, flip: 0, hi: false });
    }
    // helicopter: filtered noise chopped at the blade-pass rate
    const rn = c.createBufferSource(); rn.buffer = this.noiseBuf; rn.loop = true;
    this.rotorBp = c.createBiquadFilter(); this.rotorBp.type = 'bandpass'; this.rotorBp.frequency.value = 170; this.rotorBp.Q.value = 0.9;
    this.rotorGain = c.createGain(); this.rotorGain.gain.value = 0;
    const chop = c.createGain(); chop.gain.value = 0.5;
    this.rotorLfo = c.createOscillator(); this.rotorLfo.frequency.value = 14;
    const lfoDepth = c.createGain(); lfoDepth.gain.value = 0.5;
    this.rotorLfo.connect(lfoDepth).connect(chop.gain);
    this.rotorPan = c.createStereoPanner();
    rn.connect(this.rotorBp).connect(chop).connect(this.rotorGain).connect(this.rotorPan).connect(this.master);
    rn.start(); this.rotorLfo.start();
  }

  /**
   * Spatialise the sirens and rotor against the camera: distance attenuation, left/right pan from the camera's right
   * vector, and a Doppler shift from the radial velocity. `units` carry world position and velocity (m/s).
   */
  spatial(listener: { x: number; y: number; z: number; rx: number; rz: number }, dt: number, units: { x: number; y: number; z: number; vx: number; vy: number; vz: number; on: boolean }[], heli: { x: number; y: number; z: number; vx: number; vy: number; vz: number; on: boolean }): void {
    const c = this.ctx; if (!c || !this.engineOn) return;
    const t = c.currentTime;
    const lv = this.lastListener.has && dt > 0 ? { x: (listener.x - this.lastListener.x) / dt, y: (listener.y - this.lastListener.y) / dt, z: (listener.z - this.lastListener.z) / dt } : { x: 0, y: 0, z: 0 };
    this.lastListener = { x: listener.x, y: listener.y, z: listener.z, has: true };
    const place = (u: { x: number; y: number; z: number; vx: number; vy: number; vz: number }) => {
      const dx = u.x - listener.x, dy = u.y - listener.y, dz = u.z - listener.z;
      const d = Math.hypot(dx, dy, dz) || 1;
      const radial = ((u.vx - lv.x) * dx + (u.vy - lv.y) * dy + (u.vz - lv.z) * dz) / d; // + = receding
      const doppler = 343 / (343 + Math.max(-120, Math.min(120, radial)));
      const pan = Math.max(-1, Math.min(1, (dx * listener.rx + dz * listener.rz) / d));
      return { d, doppler, pan };
    };
    this.sirens.forEach((s, i) => {
      const u = units[i];
      if (!u || !u.on) { s.gain.gain.setTargetAtTime(0, t, 0.08); return; }
      const p = place(u);
      s.flip -= dt; if (s.flip <= 0) { s.flip = 0.42; s.hi = !s.hi; }
      s.osc.frequency.setTargetAtTime((s.hi ? 960 : 720) * p.doppler, t, 0.025);
      s.gain.gain.setTargetAtTime(this._muted ? 0 : Math.min(0.09, 5 / (1 + p.d * 0.09)), t, 0.1);
      s.pan.pan.setTargetAtTime(p.pan, t, 0.05);
    });
    if (this.rotorGain && this.rotorPan && this.rotorBp && this.rotorLfo) {
      if (!heli.on) { this.rotorGain.gain.setTargetAtTime(0, t, 0.15); return; }
      const p = place(heli);
      this.rotorGain.gain.setTargetAtTime(Math.min(0.5, 14 / (1 + p.d * 0.07)), t, 0.1);
      this.rotorPan.pan.setTargetAtTime(p.pan, t, 0.08);
      this.rotorBp.frequency.setTargetAtTime(170 * p.doppler, t, 0.1);
      this.rotorLfo.frequency.setTargetAtTime(14 * p.doppler, t, 0.1);
    }
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
  silencePursuit(): void { const c = this.ctx; if (!c) return; for (const s of this.sirens) s.gain.gain.setTargetAtTime(0, c.currentTime, 0.1); this.rotorGain?.gain.setTargetAtTime(0, c.currentTime, 0.1); }
  silence(): void { if (this.ctx && this.engineOn) { this.engineGain.gain.setTargetAtTime(0, this.ctx.currentTime, 0.1); this.tyreGain.gain.setTargetAtTime(0, this.ctx.currentTime, 0.1); } }
}
