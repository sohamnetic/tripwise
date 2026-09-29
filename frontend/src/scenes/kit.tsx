import type { Far, Ground, Sky } from "./types";
import { HORIZON } from "./types";

// ---------- sky ----------

const SKIES: Record<Sky, { top: string; bottom: string; orb: string; x: number; y: number; r: number }> = {
  dawn: { top: "#ffe4e6", bottom: "#ffd3b0", orb: "#ffb86b", x: 250, y: 175, r: 58 },
  day: { top: "#cfe6ff", bottom: "#eef7ff", orb: "#fff4c2", x: 1010, y: 95, r: 46 },
  sunset: { top: "#fff1dc", bottom: "#ffc58f", orb: "#ffb347", x: 900, y: 215, r: 78 },
  dusk: { top: "#f9c88a", bottom: "#ee956a", orb: "#ffe29a", x: 560, y: 238, r: 86 },
  night: { top: "#1b1845", bottom: "#4f46a8", orb: "#fef9c3", x: 1010, y: 85, r: 30 },
};

export function Clouds({ y = 70, opacity = 0.9 }: { y?: number; opacity?: number }) {
  return (
    <g fill="#fff" opacity={opacity}>
      <g className="anim-drift">
        <ellipse cx="180" cy={y} rx="60" ry="16" />
        <ellipse cx="215" cy={y - 12} rx="38" ry="18" />
      </g>
      <g className="anim-drift-slow">
        <ellipse cx="560" cy={y + 28} rx="72" ry="14" />
        <ellipse cx="600" cy={y + 16} rx="40" ry="17" />
      </g>
      <g className="anim-drift">
        <ellipse cx="1060" cy={y - 12} rx="52" ry="12" />
      </g>
    </g>
  );
}

export function SkyLayer({ sky, id }: { sky: Sky; id: string }) {
  const s = SKIES[sky];
  const night = sky === "night";
  return (
    <>
      <defs>
        <linearGradient id={`${id}sky`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={s.top} />
          <stop offset="1" stopColor={s.bottom} />
        </linearGradient>
      </defs>
      <rect width="1200" height="400" fill={`url(#${id}sky)`} />
      {night &&
        Array.from({ length: 34 }, (_, i) => (
          <circle key={i} cx={(i * 197 + 40) % 1200} cy={14 + ((i * 83) % 170)} r={i % 4 === 0 ? 1.8 : 1.1}
            fill="#fff" className={i % 3 ? "anim-twinkle" : "anim-twinkle-slow"} />
        ))}
      <circle cx={s.x} cy={s.y} r={s.r} fill={s.orb} className="anim-glow" />
      {night && <circle cx={s.x + 14} cy={s.y - 8} r={s.r - 3} fill="#27235e" />}
      {!night && <Clouds opacity={sky === "dusk" ? 0.55 : 0.9} />}
    </>
  );
}

// ---------- far backdrop (sits on the horizon) ----------

export function FarLayer({ far, night }: { far: Far; night: boolean }) {
  const t = (day: string, dark: string) => (night ? dark : day);
  switch (far) {
    case "peaks":
    case "barren": {
      const rock = far === "barren" ? t("#b79f86", "#4b3f5e") : t("#9db4d6", "#3c3a73");
      const near = far === "barren" ? t("#a0846a", "#3e3452") : t("#7c98c4", "#34306a");
      return (
        <>
          <path d={`M0 ${HORIZON} L150 120 L290 230 L460 80 L640 240 L820 110 L1000 235 L1200 130 V${HORIZON}z`} fill={rock} />
          <path d="M460 80 L412 138 L444 130 L462 146 L488 124 L512 134z M820 110 L776 160 L806 152 L822 166 L846 150 L862 154z M150 120 L116 160 L140 154 L156 166 L176 152z" fill="#fff" opacity={night ? 0.8 : 1} />
          <path d={`M0 ${HORIZON} L220 200 L380 262 L560 190 L760 268 L940 205 L1200 262 V${HORIZON}z`} fill={near} />
        </>
      );
    }
    case "hills":
      return (
        <>
          <path d={`M0 ${HORIZON} Q150 170 320 225 T640 205 T960 220 T1200 195 V${HORIZON}z`} fill={t("#a9c7a2", "#34405e")} />
          <path d={`M0 ${HORIZON} Q200 225 420 255 T860 240 T1200 250 V${HORIZON}z`} fill={t("#7fae7c", "#2d3a55")} />
        </>
      );
    case "dunes":
      return (
        <>
          <path d={`M0 ${HORIZON} Q180 210 380 250 T800 235 T1200 225 V${HORIZON}z`} fill={t("#f2c98b", "#5a4a6e")} />
          <path d={`M0 ${HORIZON} Q260 245 560 268 T1200 258 V${HORIZON}z`} fill={t("#e8b471", "#4b3d60")} />
        </>
      );
    case "skyline": {
      const b = [[0, 90], [70, 140], [130, 70], [190, 160], [260, 110], [330, 60], [380, 130], [450, 95],
        [880, 120], [940, 75], [1000, 150], [1070, 100], [1130, 135]];
      return (
        <g fill={t("#b9c3d6", "#2a2566")}>
          {b.map(([x, h]) => <rect key={x} x={x} y={HORIZON - h} width="56" height={h} />)}
          {night && b.map(([x, h]) =>
            Array.from({ length: Math.floor(h / 26) }, (_, r) => (
              <rect key={`${x}-${r}`} x={x + 10 + (r % 2) * 18} y={HORIZON - h + 10 + r * 26} width="8" height="10" fill="#fcd34d" opacity="0.8" />
            )),
          )}
        </g>
      );
    }
    case "forest":
      return (
        <g fill={t("#4f8a5b", "#23384a")}>
          {Array.from({ length: 30 }, (_, i) => {
            const x = i * 42 - 10;
            const h = 40 + ((i * 37) % 45);
            return <ellipse key={i} cx={x} cy={HORIZON - h / 2} rx="34" ry={h / 2 + 10} />;
          })}
          <rect y={HORIZON - 12} width="1200" height="12" />
        </g>
      );
    case "palms":
      return (
        <g>
          <rect y={HORIZON - 10} width="1200" height="10" fill={t("#5f9a5a", "#23384a")} />
          {Array.from({ length: 16 }, (_, i) => {
            const x = 30 + i * 78 + ((i * 29) % 30);
            const h = 50 + ((i * 17) % 35);
            return (
              <g key={i} stroke={t("#4d7a45", "#23384a")} fill={t("#3f7f4a", "#1f3446")}>
                <path d={`M${x} ${HORIZON - 6} q4 ${-h / 2} ${-2} ${-h}`} strokeWidth="3" fill="none" />
                <path d={`M${x - 2} ${HORIZON - h - 6} q-22 -6 -30 12 q14 -10 30 -12z M${x - 2} ${HORIZON - h - 6} q22 -8 30 10 q-14 -10 -30 -10z M${x - 2} ${HORIZON - h - 6} q-6 -20 6 -26 q-2 14 -6 26z`} strokeWidth="0" />
              </g>
            );
          })}
        </g>
      );
    default:
      return null;
  }
}

// ---------- ground: back (behind landmark & movers) and front (foreground) ----------

function Waves({ y, color = "#fff", opacity = 0.3, slow = false }: { y: number; color?: string; opacity?: number; slow?: boolean }) {
  const step = slow ? 120 : 100;
  let d = `M0 ${y}`;
  for (let x = 0; x < 2400; x += step) d += ` q${step / 2} -8 ${step} 0`;
  d += " v5 h-2400z";
  return <path d={d} fill={color} opacity={opacity} className={slow ? "anim-wave-slow" : "anim-wave"} />;
}

export function GroundBack({ ground, id, night }: { ground: Ground; id: string; night: boolean }) {
  const t = (day: string, dark: string) => (night ? dark : day);
  const water = (top: string, bottom: string, from = HORIZON) => (
    <>
      <defs>
        <linearGradient id={`${id}water`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={top} />
          <stop offset="1" stopColor={bottom} />
        </linearGradient>
      </defs>
      <rect y={from} width="1200" height={400 - from} fill={`url(#${id}water)`} />
    </>
  );
  switch (ground) {
    case "sea":
      return <>{water(t("#2bb3a0", "#264a7a"), t("#0d8573", "#162c55"))}<Waves y={292} /><Waves y={318} slow opacity={0.2} /></>;
    case "ocean":
      return (
        <>
          {water(t("#3fd0c9", "#24507e"), t("#0a7fa3", "#13294f"))}
          <Waves y={290} opacity={0.35} />
          <g fill="#fff" opacity="0.08">
            <path d="M200 290 L140 400 H180 L230 290z M600 290 L560 400 H610 L640 290z M950 290 L930 400 H980 L990 290z" />
          </g>
        </>
      );
    case "lake":
      return (
        <>
          {water(t("#6fa8d6", "#2e3f7a"), t("#3f78b0", "#1b2552"))}
          <g stroke="#fff" strokeWidth="2" strokeLinecap="round" opacity="0.35">
            <path className="anim-drift" d="M120 320 h60 M360 350 h90 M820 330 h70 M1000 365 h60 M540 380 h50" />
          </g>
        </>
      );
    case "river":
      return (
        <>
          {water(t("#8fb6c9", "#3a3f78"), t("#5d8aa3", "#20264f"), HORIZON + 14)}
          <rect y={HORIZON} width="1200" height="14" fill={t("#c9b08a", "#4a3f5e")} />
          <Waves y={312} opacity={0.22} slow />
        </>
      );
    case "backwater":
      return (
        <>
          {water(t("#5fa58c", "#26485a"), t("#2f7a64", "#152e3c"))}
          <g stroke="#fff" strokeWidth="2" strokeLinecap="round" opacity="0.25">
            <path className="anim-drift-slow" d="M180 330 h80 M520 360 h70 M880 340 h90" />
          </g>
        </>
      );
    case "grass":
      return <rect y={HORIZON} width="1200" height="120" fill={t("#8cc47e", "#2c4a46")} />;
    case "snow":
      return (
        <>
          <rect y={HORIZON} width="1200" height="120" fill={t("#f4f8ff", "#c7cde6")} />
          <path d="M0 330 Q300 300 620 340 T1200 320 V400 H0z" fill={t("#e3ecfa", "#b3badb")} />
        </>
      );
    case "sand":
      return <rect y={HORIZON} width="1200" height="120" fill={t("#f3cf94", "#6b5a78")} />;
    case "city":
      return (
        <>
          <rect y={HORIZON} width="1200" height="120" fill={t("#d7dbe3", "#3a3668")} />
          <rect y="342" width="1200" height="44" fill={t("#6b7280", "#23204a")} />
          <path d="M0 364 h1200" stroke="#fff" strokeWidth="3" strokeDasharray="26 22" opacity="0.7" />
        </>
      );
    case "rocky":
      return (
        <>
          <rect y={HORIZON} width="1200" height="120" fill={t("#d9b98a", "#5a4a6a")} />
          <g fill={t("#b88d62", "#4a3b58")}>
            <circle cx="110" cy="300" r="34" /><circle cx="160" cy="290" r="26" /><circle cx="135" cy="262" r="20" />
            <circle cx="1060" cy="296" r="40" /><circle cx="1120" cy="300" r="28" /><circle cx="1090" cy="258" r="22" />
            <circle cx="420" cy="306" r="22" /><circle cx="960" cy="310" r="18" />
          </g>
        </>
      );
    case "salt":
      return (
        <>
          <rect y={HORIZON} width="1200" height="120" fill={t("#f7f6f1", "#cfd2e8")} />
          <g stroke={t("#dedbd0", "#a9acc8")} strokeWidth="1.5" fill="none">
            <path d="M0 320 l120 -10 l90 30 l140 -20 l120 24 l160 -18 l150 26 l140 -22 l140 14 l140 -12 M60 370 l140 -14 l130 22 l150 -18 l120 20 l160 -16 l140 20 l150 -14" />
          </g>
        </>
      );
    case "rows":
      return (
        <>
          <rect y={HORIZON} width="1200" height="120" fill={t("#6fae62", "#284a44")} />
          <g stroke={t("#4f8f47", "#1e3a36")} strokeWidth="7" fill="none" strokeLinecap="round">
            {Array.from({ length: 7 }, (_, i) => (
              <path key={i} d={`M-20 ${294 + i * 16} Q300 ${282 + i * 16} 600 ${296 + i * 16} T1220 ${290 + i * 16}`} />
            ))}
          </g>
        </>
      );
  }
}

export function GroundFront({ ground, night }: { ground: Ground; night: boolean }) {
  const t = (day: string, dark: string) => (night ? dark : day);
  switch (ground) {
    case "sea":
      return (
        <>
          <path d="M0 356 Q300 336 620 360 T1200 356 V400 H0z" fill={t("#f8dfb0", "#7a6a86")} />
          <path d="M0 376 Q360 358 700 374 T1200 372 V400 H0z" fill={t("#f3d19a", "#6a5b78")} />
          <Palm x={1110} night={night} />
        </>
      );
    case "backwater":
      return (
        <>
          <path d="M0 372 Q200 356 420 376 V400 H0z" fill={t("#4d8a4a", "#1d3834")} />
          <Palm x={90} night={night} />
          <Palm x={200} night={night} flip />
        </>
      );
    case "river":
      return (
        <g fill={t("#b08a66", "#4a3a5a")}>
          {[0, 1, 2].map((i) => <rect key={i} x={-10} y={372 + i * 9} width={260 - i * 30} height="9" />)}
        </g>
      );
    case "sand":
      return <path d="M0 360 Q300 330 640 358 T1200 350 V400 H0z" fill={t("#e9b56c", "#5b4a6a")} />;
    case "grass":
      return (
        <g fill={t("#6fae62", "#223e3a")}>
          <path d="M0 370 Q320 344 660 368 T1200 362 V400 H0z" />
        </g>
      );
    default:
      return null;
  }
}

export function Palm({ x, night, flip = false }: { x: number; night: boolean; flip?: boolean }) {
  return (
    <g transform={`translate(${x - 150} 0)${flip ? ` scale(-1 1) translate(${-300} 0)` : ""}`}>
      {/* trunk base (x 150) sits ~38% across the palm's bounding box */}
      <g className="anim-sway" style={{ transformBox: "fill-box", transformOrigin: "38% 100%" }}>
        <path d="M150 395 C158 330 150 280 176 220" stroke={night ? "#3b2d3f" : "#8a5a44"} strokeWidth="10" fill="none" strokeLinecap="round" />
        <g fill={night ? "#1c3a36" : "#1f7a4f"}>
          <path d="M176 220 q-70 -20 -110 30 q60 -30 110 -30z" />
          <path d="M176 220 q-40 -60 -100 -60 q60 20 100 60z" />
          <path d="M176 220 q20 -70 80 -80 q-50 30 -80 80z" />
          <path d="M176 220 q80 -10 110 50 q-50 -45 -110 -50z" />
        </g>
      </g>
    </g>
  );
}
