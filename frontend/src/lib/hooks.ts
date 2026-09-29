import { useEffect, useRef, useState } from "react";

const reducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** Animates from 0 to `value` once, easing out. */
export function useCountUp(value: number, ms = 900) {
  const [shown, setShown] = useState(() => (reducedMotion() ? value : 0));
  useEffect(() => {
    if (reducedMotion()) {
      setShown(value);
      return;
    }
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / ms);
      setShown(Math.round(value * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, ms]);
  return shown;
}

/** True once the element has scrolled into view (stays true). */
export function useInView<T extends Element>() {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || inView) return;
    if (!("IntersectionObserver" in window)) {
      setInView(true);
      return;
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          io.disconnect();
        }
      },
      { rootMargin: "0px 0px -8% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [inView]);
  return [ref, inView] as const;
}

/** Cycles through 0..n-1 every `ms`; with `stop`, counts up once to n-1 and stays there. */
export function useRotate(n: number, ms: number, paused = false, stop = false) {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (n < 2 || paused) return;
    const t = setInterval(() => setI((x) => (stop ? Math.min(x + 1, n - 1) : (x + 1) % n)), ms);
    return () => clearInterval(t);
  }, [n, ms, paused, stop]);
  return i;
}
