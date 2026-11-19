import { Phase } from '../sim/types';

/** Top-level screen flow. */
export type Screen = 'loading' | 'lodge' | 'descent' | 'wreck' | 'fade';

export type FlowEvent =
  | { t: 'ready' }
  | { t: 'go' }
  | { t: 'phase'; phase: Phase }
  | { t: 'wreckDone' }
  | { t: 'faded' }
  | { t: 'restart' };

/** Pure transition function; the Game owns the side effects. */
export function nextScreen(s: Screen, e: FlowEvent): Screen {
  switch (e.t) {
    case 'ready': return s === 'loading' ? 'lodge' : s;
    case 'go': return s === 'lodge' ? 'descent' : s;
    case 'phase': return s === 'descent' && e.phase === Phase.Wrecked ? 'wreck' : s;
    case 'wreckDone': return s === 'wreck' ? 'fade' : s;
    case 'faded': return s === 'fade' ? 'lodge' : s;
    case 'restart': return s === 'loading' ? s : 'lodge';
  }
}

/** Wreck-sequence timeline in seconds since Wrecked began (matches state()[35]). */
export const WRECK = { orbit: 9, pull: 4, fade: 1.2, hold: 1.0 } as const;
export const WRECK_TOTAL = WRECK.orbit + WRECK.pull;
