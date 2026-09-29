import { useEffect, useId, useRef, useState } from "react";
import { GroundBack, GroundFront, FarLayer, SkyLayer } from "../scenes/kit";
import { LANDMARKS } from "../scenes/landmarks";
import { MOTIONS } from "../scenes/motions";
import { HORIZON, REFLECTS, WATER, type SceneSpec } from "../scenes/types";
import { vibeFor } from "../lib/vibes";

// An animated SVG landscape for a destination: its sky, backdrop, ground, landmark and
// things moving about. Fills its parent (give the parent `relative overflow-hidden`).

// landmarks that already include their own base on the water
const SELF_BASED = new Set(["rockMemorial", "waterVillas"]);

interface Props {
  city?: string;
  spec?: SceneSpec;
  className?: string;
  /** Thumbnails: stay still until the card (a `.group`) is hovered. */
  still?: boolean;
}

// Draw a scene only once it comes near the screen, and pause it while it's off screen.
// (A page like /destinations has 100+ scenes; only a dozen are ever visible at once.)
function useOnScreen<T extends Element>() {
  const ref = useRef<T>(null);
  const supported = typeof window !== "undefined" && "IntersectionObserver" in window;
  const [on, setOn] = useState(!supported);
  const [seen, setSeen] = useState(!supported);
  useEffect(() => {
    const el = ref.current;
    if (!el || !supported) return;
    const io = new IntersectionObserver(([e]) => {
      setOn(e.isIntersecting);
      if (e.isIntersecting) setSeen(true);
    }, { rootMargin: "200px" });
    io.observe(el);
    return () => io.disconnect();
  }, [supported]);
  return [ref, on, seen] as const;
}

export default function Scene({ city, spec, className = "", still = false }: Props) {
  const id = useId().replace(/:/g, "");
  const [ref, onScreen, seen] = useOnScreen<SVGSVGElement>();
  const s = spec ?? vibeFor(city).spec;
  const night = s.sky === "night";
  const Landmark = s.landmark ? LANDMARKS[s.landmark] : null;
  const water = WATER.has(s.ground);
  const baseY = water ? HORIZON + 10 : HORIZON + 20;
  const lx = s.lx ?? 700;
  const ls = s.ls ?? 1;

  return (
    <svg ref={ref} viewBox="0 0 1200 400" preserveAspectRatio="xMidYMax slice" aria-hidden="true"
      className={`absolute inset-0 h-full w-full ${onScreen ? "" : "scene-paused"} ${still ? "scene-still" : ""} ${className}`}>
      <SkyLayer sky={s.sky} id={id} />
      {seen && (<>
      <FarLayer far={s.far} night={night} />
      <GroundBack ground={s.ground} id={id} night={night} />
      {Landmark && REFLECTS.has(s.ground) && (
        <g transform={`translate(${lx} ${baseY}) scale(${ls} ${-ls * 0.8})`} opacity="0.22">
          <Landmark />
        </g>
      )}
      {Landmark && (
        <g transform={`translate(${lx} ${baseY}) scale(${ls})`}>
          {/* on open sea, stand the landmark on a rocky point */}
          {(s.ground === "sea" || s.ground === "ocean") && !SELF_BASED.has(s.landmark!) && (
            <path d="M-130 14 C-110 -6 -50 -14 0 -12 C60 -14 120 -6 150 14z" fill={night ? "#3d3552" : "#7d6e5d"} />
          )}
          <Landmark />
        </g>
      )}
      {s.motions.map((m) => {
        const Move = MOTIONS[m];
        return <Move key={m} />;
      })}
      <GroundFront ground={s.ground} night={night} />
      </>)}
    </svg>
  );
}
