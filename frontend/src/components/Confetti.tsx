import { useMemo, type CSSProperties } from "react";

const COLORS = ["#14a38b", "#f5b544", "#f06a4f", "#6d5bd0", "#2f7fd8", "#c2417a"];

// A one-off burst of falling confetti. Mount it (with a new `key`) to replay.
export default function Confetti({ pieces = 90 }: { pieces?: number }) {
  const bits = useMemo(
    () =>
      Array.from({ length: pieces }, (_, i) => ({
        left: Math.random() * 100,
        delay: Math.random() * 0.6,
        duration: 1.8 + Math.random() * 1.6,
        dx: `${(Math.random() - 0.5) * 240}px`,
        rot: `${Math.random() * 720 - 360}deg`,
        color: COLORS[i % COLORS.length],
        w: 6 + Math.random() * 6,
        round: Math.random() > 0.6,
      })),
    [pieces],
  );
  return (
    <div className="pointer-events-none fixed inset-0 z-[2000] overflow-hidden" aria-hidden="true">
      {bits.map((b, i) => (
        <span
          key={i}
          style={{
            position: "absolute",
            top: 0,
            left: `${b.left}%`,
            width: b.w,
            height: b.round ? b.w : b.w * 0.45,
            background: b.color,
            borderRadius: b.round ? 9999 : 2,
            animation: `confetti-fall ${b.duration}s cubic-bezier(0.25, 0.6, 0.4, 1) ${b.delay}s forwards`,
            "--dx": b.dx,
            "--rot": b.rot,
          } as CSSProperties}
        />
      ))}
    </div>
  );
}
