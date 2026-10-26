import { memo, useEffect, useRef, useState, useSyncExternalStore } from 'react';

import styles from './SplitFlapStyle.module.css';

// Flaps of a real board, in the order the drum turns
const DRUM = ' ABCDEFGHIJKLMNOPQRSTUVWXYZÑ0123456789.@-_+:#';
// Time between one flap and the next, the same as the fall animation of SplitFlapStyle.module.css
const FLAP_MS = 55;
// Delay between one cell and the next, so a word settles left to right
const CELL_STAGGER_MS = 18;

const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

function subscribeToReducedMotion(onChange) {
  reducedMotionQuery.addEventListener('change', onChange);
  return () => reducedMotionQuery.removeEventListener('change', onChange);
}

// "Reduce motion" of the system, followed live while the page is open
function useReducedMotion() {
  return useSyncExternalStore(subscribeToReducedMotion, () => reducedMotionQuery.matches);
}

// Flaps the drum shows on its way to the target: only the last 4 to 9, a random number so cells don't settle in sync
function flapsTo(from, to) {
  const start = DRUM.indexOf(from);
  const end = DRUM.indexOf(to);
  // A character the drum doesn't have just flips once
  if (start === -1 || end === -1) return [to];

  const path = [];
  for (let i = start; i !== end; i = (i + 1) % DRUM.length) path.push(DRUM[(i + 1) % DRUM.length]);
  return path.slice(-(4 + Math.floor(Math.random() * 6)));
}

// One character: when it changes, it falls through the flaps of the drum until it shows the new one
function FlapCell({ target, delay, reducedMotion }) {
  // shown: character on the cell, previous: the one folding away on top of it, flips: remounts the fold
  const [flap, setFlap] = useState({ shown: ' ', previous: ' ', flips: 0 });
  // The character on the cell right now. Not flap.shown: a flap of the previous target can land after
  // the render with the new target and before its effect, and the drum would start from a stale character
  const shownRef = useRef(' ');

  // Only a new target starts the drum, the shown character changes on every flap
  useEffect(() => {
    if (reducedMotion) return;

    const steps = flapsTo(shownRef.current, target);
    const timers = steps.map((char, index) =>
      setTimeout(() => {
        shownRef.current = char;
        setFlap((current) => ({ shown: char, previous: current.shown, flips: current.flips + 1 }));
      }, delay + index * FLAP_MS),
    );
    return () => timers.forEach(clearTimeout);
  }, [target, delay, reducedMotion]);

  const shown = reducedMotion ? target : flap.shown;

  return (
    <span className={styles.cell}>
      <span className={styles.glyph}>{shown}</span>
      {flap.flips > 0 && !reducedMotion && (
        <span key={flap.flips} className={styles.fold}>
          {flap.previous}
        </span>
      )}
    </span>
  );
}

// A row of flap cells showing text, uppercase, padded to length or cut with "…". Hidden from screen readers:
// the page gives them the real text next to it
function SplitFlap({ text, length, delay = 0 }) {
  const reducedMotion = useReducedMotion();
  const upper = text.toUpperCase();
  const chars = upper.length > length ? `${upper.slice(0, length - 1)}…` : upper.padEnd(length, ' ');

  return (
    <span className={styles.flaps} style={{ '--length': length }} aria-hidden="true">
      {[...chars].map((char, index) => (
        <FlapCell
          key={index}
          target={char}
          delay={delay + index * CELL_STAGGER_MS}
          reducedMotion={reducedMotion}
        />
      ))}
    </span>
  );
}

// memo: the page re-renders on every key typed in its form, the board only when its text changes
export default memo(SplitFlap);
