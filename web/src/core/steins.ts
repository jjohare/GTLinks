/** Stein loading state machine: GO is locked below MIN, the pile is capped at MAX. */
export const MIN_STEINS = 10;
export const MAX_STEINS = 15;

export class SteinLoad {
  /** Stein ids (0..MAX-1) currently on the car, in stacking order. */
  private onCar: number[] = [];

  get count(): number { return this.onCar.length; }
  get canGo(): boolean { return this.onCar.length >= MIN_STEINS; }
  get full(): boolean { return this.onCar.length >= MAX_STEINS; }
  get ids(): readonly number[] { return this.onCar; }
  has(id: number): boolean { return this.onCar.includes(id); }

  /** Put a specific stein on the car. Returns false when full, unknown or already loaded. */
  add(id: number): boolean {
    if (this.full || id < 0 || id >= MAX_STEINS || this.has(id)) return false;
    this.onCar.push(id);
    return true;
  }
  /** Put the lowest-numbered stein still on the table on the car. */
  addNext(): number | null {
    for (let i = 0; i < MAX_STEINS; i++) if (!this.has(i)) return this.add(i) ? i : null;
    return null;
  }
  remove(id: number): boolean {
    const i = this.onCar.indexOf(id);
    if (i < 0) return false;
    this.onCar.splice(i, 1);
    return true;
  }
  /** Take the most recently loaded stein off. */
  removeLast(): number | null {
    return this.onCar.length ? (this.onCar.pop() as number) : null;
  }
  clear(): void { this.onCar = []; }
  /** Handling severity, 0 at the minimum to 1 at the maximum (contract section 5). */
  get severity(): number { return Math.max(0, Math.min(1, (this.count - MIN_STEINS) / (MAX_STEINS - MIN_STEINS))); }
}
