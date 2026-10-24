// jsdom has no matchMedia: a fake one where the tests decide whether the system is in dark mode
// and whether it asks for reduced motion
function fakeQuery() {
  const listeners = new Set();
  return {
    matches: false,
    addEventListener: (_event, listener) => listeners.add(listener),
    removeEventListener: (_event, listener) => listeners.delete(listener),
    // Changes the value and tells whoever is listening, like the browser does
    set(matches) {
      this.matches = matches;
      listeners.forEach((listener) => listener());
    },
  };
}

const queries = {
  '(prefers-color-scheme: dark)': fakeQuery(),
  '(prefers-reduced-motion: reduce)': fakeQuery(),
};

// Any other query never matches
const otherQuery = { matches: false, addEventListener() {}, removeEventListener() {} };

window.matchMedia = (query) => queries[query] ?? otherQuery;

export function setSystemDark(dark) {
  queries['(prefers-color-scheme: dark)'].set(dark);
}

export function setReducedMotion(reduce) {
  queries['(prefers-reduced-motion: reduce)'].set(reduce);
}
