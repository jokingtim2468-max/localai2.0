import { useEffect, useRef, useState } from "react";

// Thinking indicator: a moon crossing a sun (an eclipse), plus a changing word and a timer.
// Web Animations API, not CSS keyframes, so it still runs when the OS animation setting
// is off; prefers-reduced-motion slows it rather than freezing it.
const WORDS = ["Thinking", "Reading the code", "Planning", "Working it out", "Checking", "Tracing"];

export function Working({ label }: { label: string }) {
  const moon = useRef<HTMLElement>(null);
  const [tick, setTick] = useState(0);
  const [t0] = useState(Date.now());
  useEffect(() => {
    const slow = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const a = moon.current?.animate(
      [{ transform: "translateX(-110%)" }, { transform: "translateX(110%)" }],
      { duration: slow ? 6000 : 1800, iterations: Infinity, easing: "ease-in-out" });
    const id = setInterval(() => setTick((n) => n + 1), 1000);
    return () => { a?.cancel(); clearInterval(id); };
  }, []);
  const s = Math.round((Date.now() - t0) / 1000);
  const word = label || WORDS[Math.floor(tick / 3) % WORDS.length] + "…";
  return (
    <div className="working" role="status">
      <span className="eclipse"><i ref={moon} /></span>
      <span>{word}</span>
      {s >= 2 && <span className="t">{s}s</span>}
    </div>
  );
}
