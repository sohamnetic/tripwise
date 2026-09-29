import type { CSSProperties, ReactElement, ReactNode } from "react";
import type { Motion } from "./types";

// Things that move through a scene. Crossing movers are drawn around x = 0 and slide
// across the full width with .anim-cross / .anim-cross-rev (see index.css).

function Cross({ y, dur, delay = 0, rev = false, bob, children }: { y: number; dur: number; delay?: number; rev?: boolean; bob?: string; children: ReactNode }) {
  const style: CSSProperties = { animationDuration: `${dur}s`, animationDelay: `${-delay}s` };
  return (
    <g transform={`translate(0 ${y})`}>
      <g className={rev ? "anim-cross-rev" : "anim-cross"} style={style}>
        {bob ? <g className={bob}>{children}</g> : children}
      </g>
    </g>
  );
}

const flip = (c: ReactNode) => <g transform="scale(-1 1)">{c}</g>;

function Rower({ x = 0 }: { x?: number }) {
  return (
    <g>
      <circle cx={x} cy="-14" r="3.5" fill="#1f2937" />
      <path d={`M${x} -10 v8 M${x - 2} -6 l14 12`} stroke="#1f2937" strokeWidth="2" />
    </g>
  );
}

const M: Record<Motion, () => ReactElement> = {
  sailboat: () => (
    <Cross y={304} dur={52} delay={14} bob="anim-bob">
      <path d="M-40 0 h80 l-14 14 h-52z" fill="#8a5a44" />
      <path d="M-2 0 v-54 l34 48z" fill="#fff" />
      <path d="M-6 -4 v-40 l-24 38z" fill="#f1f5f9" />
    </Cross>
  ),

  rowboats: () => (
    <>
      <Cross y={322} dur={60} delay={20} rev bob="anim-bob-slow">
        <path d="M-30 0 q30 10 60 0 l-6 8 h-48z" fill="#5b3a29" />
        <Rower />
      </Cross>
      <Cross y={346} dur={74} delay={50} rev bob="anim-bob">
        <path d="M-26 0 q26 9 52 0 l-5 7 h-42z" fill="#6f4328" />
        <Rower x={-4} />
      </Cross>
    </>
  ),

  houseboat: () => (
    <Cross y={332} dur={85} delay={30} bob="anim-bob-slow">
      <path d="M-95 0 q95 20 190 0 l-12 12 q-83 12 -166 0z" fill="#4a2f22" />
      <path d="M-70 0 q70 -52 140 0z" fill="#c9a063" />
      {[-40, -14, 12, 38].map((x) => <path key={x} d={`M${x} ${-Math.round(26 - Math.abs(x) / 3)} v${Math.round(22 - Math.abs(x) / 4)}`} stroke="#8a6a3c" strokeWidth="2" />)}
      <path d="M-70 0 q70 -52 140 0" fill="none" stroke="#a88246" strokeWidth="3" />
    </Cross>
  ),

  shikara: () => (
    <>
      <Cross y={336} dur={64} delay={10} bob="anim-bob-slow">
        <path d="M-80 0 q80 12 160 0 l-8 6 q-72 8 -144 0z" fill="#7a3e2b" />
        <rect x="-40" y="-24" width="70" height="20" fill="#d9465f" />
        <path d="M-44 -24 h78" stroke="#f59e0b" strokeWidth="4" strokeDasharray="6 4" />
        {[-38, -4, 28].map((x) => <path key={x} d={`M${x} -4 v-20`} stroke="#5b3a29" strokeWidth="2" />)}
        <Rower x={56} />
      </Cross>
      <Cross y={360} dur={90} delay={60} rev bob="anim-bob">
        {flip(<><path d="M-70 0 q70 10 140 0 l-7 6 q-63 7 -126 0z" fill="#6b3a2a" /><rect x="-34" y="-20" width="60" height="16" fill="#2f7fd8" /><Rower x={48} /></>)}
      </Cross>
    </>
  ),

  raft: () => (
    <Cross y={338} dur={17} delay={6} bob="anim-bob">
      <ellipse cx="0" cy="0" rx="52" ry="11" fill="#f59e0b" />
      {[-30, -10, 10, 30].map((x, i) => (
        <g key={x}>
          <circle cx={x} cy="-12" r="5" fill={["#dc2626", "#2563eb", "#16a34a", "#dc2626"][i]} />
          <path d={`M${x} -7 l${i % 2 ? 12 : -12} 16`} stroke="#1f2937" strokeWidth="2" />
        </g>
      ))}
    </Cross>
  ),

  diyas: () => (
    <g>
      {[160, 300, 450, 620, 780, 930, 1070].map((x, i) => (
        <g key={x} className={i % 2 ? "anim-bob" : "anim-bob-slow"}>
          <circle cx={x} cy={344 + (i % 3) * 14} r="10" fill="#ffd166" opacity="0.35" />
          <path d={`M${x - 8} ${348 + (i % 3) * 14} h16 l-4 5 h-8z`} fill="#b45309" />
          <path d={`M${x} ${337 + (i % 3) * 14} q4 5 0 10 q-4 -5 0 -10z`} fill="#fde047" />
        </g>
      ))}
    </g>
  ),

  fish: () => (
    <>
      {[[338, 22, 0, "#f97316"], [360, 30, 8, "#facc15"], [382, 26, 16, "#38bdf8"], [350, 36, 22, "#fb7185"], [372, 20, 4, "#a3e635"]].map(([y, dur, delay, c], i) => (
        <Cross key={i} y={y as number} dur={dur as number} delay={delay as number} rev={i % 2 === 1} bob="anim-wiggle">
          {(i % 2 ? flip : (x: ReactNode) => x)(<g><path d="M0 0 q14 -9 28 0 q-14 9 -28 0z" fill={c as string} /><path d="M0 0 l-9 -7 v14z" fill={c as string} /><circle cx="21" cy="-1.5" r="1.5" fill="#1f2937" /></g>)}
        </Cross>
      ))}
      {[240, 520, 860].map((x, i) => (
        <circle key={x} cx={x} cy="390" r="3" fill="#fff" opacity="0.6" className="anim-bubble" style={{ animationDelay: `${-i * 1.1}s` }} />
      ))}
    </>
  ),

  dolphins: () => (
    <g>
      {[[380, 0], [440, 1.6]].map(([x, d]) => (
        <g key={x} transform={`translate(${x} 300)`}>
          <g className="anim-jump" style={{ animationDelay: `${-d}s` }}>
            <path d="M-26 0 q20 -18 46 -4 l8 -6 l-2 9 q-24 10 -52 1z" fill="#5b7c99" />
            <path d="M0 -10 l-6 -8 l10 4z" fill="#5b7c99" />
          </g>
        </g>
      ))}
    </g>
  ),

  surfer: () => (
    <Cross y={300} dur={38} delay={8} bob="anim-bob">
      <path d="M-50 10 q30 -26 70 -10 q-10 2 -14 10z" fill="#fff" opacity="0.8" />
      <ellipse cx="0" cy="2" rx="26" ry="4" fill="#f59e0b" />
      <circle cx="0" cy="-24" r="4" fill="#1f2937" />
      <path d="M0 -20 v12 M0 -8 l-8 10 M0 -8 l8 10 M0 -16 l-10 -4 M0 -16 l10 -2" stroke="#1f2937" strokeWidth="2.5" strokeLinecap="round" />
    </Cross>
  ),

  birds: () => (
    <Cross y={110} dur={46} delay={12}>
      <g stroke="#334155" strokeWidth="2.2" fill="none" strokeLinecap="round">
        <path d="M0 0 q8 -8 16 0 q8 -8 16 0" />
        <path d="M44 -22 q6 -6 12 0 q6 -6 12 0" />
        <path d="M82 6 q5 -5 10 0 q5 -5 10 0" />
      </g>
    </Cross>
  ),

  kites: () => (
    <g>
      {[[420, 90, "#f06a4f", "anim-float"], [900, 70, "#6d5bd0", "anim-float-slow"], [1080, 140, "#f5b544", "anim-float"]].map(([x, y, c, a]) => (
        <g key={x as number} className={a as string}>
          <path d={`M${x} ${y} l18 22 l-18 22 l-18 -22z`} fill={c as string} />
          <path d={`M${x} ${(y as number) + 44} q10 30 -6 60`} stroke={c as string} strokeWidth="1.5" fill="none" />
        </g>
      ))}
    </g>
  ),

  balloons: () => (
    <>
      <g transform="translate(300 150)">
        <g className="anim-float-slow"><Balloon colors={["#f06a4f", "#f5b544"]} /></g>
      </g>
      <Cross y={90} dur={120} delay={40}>
        <g transform="scale(0.7)"><Balloon colors={["#6d5bd0", "#38bdf8"]} /></g>
      </Cross>
    </>
  ),

  paraglider: () => (
    <>
      {[0, 18].map((d, i) => (
        <g key={d} transform={`translate(0 ${i ? 60 : 110})`}>
          <g className="anim-glide" style={{ animationDelay: `${-d}s`, animationDuration: `${36 + i * 8}s` }}>
            <path d="M-40 0 q40 -26 80 0 q-40 -10 -80 0z" fill={i ? "#f5b544" : "#f06a4f"} />
            <path d="M-38 0 L0 40 L38 0 M-14 -5 L0 40 L14 -5" stroke="#374151" strokeWidth="0.8" fill="none" />
            <circle cx="0" cy="42" r="4" fill="#1f2937" />
          </g>
        </g>
      ))}
    </>
  ),

  gondola: () => (
    <g>
      <path d="M100 250 L1200 70" stroke="#374151" strokeWidth="2" />
      {[0, 7].map((d) => (
        <g key={d} transform="translate(100 250)">
          <g className="anim-cable" style={{ animationDelay: `${-d}s` }}>
            <path d="M0 0 v14" stroke="#374151" strokeWidth="2" />
            <rect x="-13" y="14" width="26" height="20" rx="4" fill="#dc2626" />
            <rect x="-9" y="18" width="18" height="8" fill="#e0f2fe" />
          </g>
        </g>
      ))}
    </g>
  ),

  snow: () => (
    <g fill="#fff">
      {Array.from({ length: 46 }, (_, i) => (
        <circle key={i} cx={(i * 131) % 1200} cy={-10} r={1.5 + (i % 3)} opacity="0.9" className="anim-fall"
          style={{ animationDuration: `${7 + (i % 6)}s`, animationDelay: `${-((i * 1.7) % 12)}s` }} />
      ))}
    </g>
  ),

  rain: () => (
    <g stroke="#dbeafe" strokeWidth="1.5" opacity="0.7">
      {Array.from({ length: 60 }, (_, i) => (
        <path key={i} d={`M${(i * 97) % 1200} -20 l-6 16`} className="anim-rain"
          style={{ animationDuration: `${0.9 + (i % 5) * 0.12}s`, animationDelay: `${-((i * 0.37) % 1.4)}s` }} />
      ))}
    </g>
  ),

  toyTrain: () => (
    <>
      <path d="M0 354 H1200" stroke="#6b4a2f" strokeWidth="3" />
      <path d="M0 358 H1200" stroke="#8a6a4a" strokeWidth="4" strokeDasharray="4 12" />
      <Cross y={350} dur={30} delay={10}>
        {[-150, -100, -50].map((x) => (
          <g key={x}>
            <rect x={x} y="-26" width="44" height="24" rx="3" fill="#2f5fa8" />
            <rect x={x + 4} y="-22" width="36" height="8" fill="#e0f2fe" />
            <circle cx={x + 10} cy="0" r="4" fill="#1f2937" /><circle cx={x + 34} cy="0" r="4" fill="#1f2937" />
          </g>
        ))}
        <rect x="0" y="-30" width="50" height="28" rx="3" fill="#1d4e89" />
        <rect x="30" y="-42" width="8" height="14" fill="#1f2937" />
        <circle cx="12" cy="0" r="5" fill="#1f2937" /><circle cx="38" cy="0" r="5" fill="#1f2937" />
        {[0, 0.7, 1.4].map((d) => <circle key={d} cx="34" cy="-48" r="7" fill="#f1f5f9" className="anim-puff" style={{ animationDelay: `${-d}s` }} />)}
      </Cross>
    </>
  ),

  camels: () => (
    <Cross y={356} dur={80} delay={20}>
      {[0, 70, 140].map((x, i) => (
        <g key={x} transform={`translate(${-x} 0)`} className="anim-walk" style={{ animationDelay: `${-i * 0.3}s` }}>
          <Camel rider={i === 0} />
        </g>
      ))}
    </Cross>
  ),

  bike: () => (
    <Cross y={366} dur={15} delay={4}>
      <circle cx="-14" cy="0" r="8" fill="none" stroke="#1f2937" strokeWidth="3" />
      <circle cx="16" cy="0" r="8" fill="none" stroke="#1f2937" strokeWidth="3" />
      <path d="M-14 0 L-2 -12 H10 L16 0 M-2 -12 L-6 -16" stroke="#b91c1c" strokeWidth="4" fill="none" />
      <circle cx="0" cy="-30" r="5" fill="#f59e0b" />
      <path d="M0 -25 L-4 -12 M0 -22 L10 -16" stroke="#1f2937" strokeWidth="3" />
    </Cross>
  ),

  rickshaw: () => (
    <Cross y={372} dur={18} delay={6}>
      <path d="M-24 -4 V-26 q0 -8 10 -8 H18 q10 0 12 10 V-4z" fill="#16a34a" />
      <path d="M-26 -30 q0 -8 10 -8 H22 q8 0 10 8z" fill="#facc15" />
      <rect x="-18" y="-26" width="14" height="10" fill="#e0f2fe" />
      <circle cx="-14" cy="0" r="6" fill="#1f2937" /><circle cx="22" cy="0" r="6" fill="#1f2937" />
    </Cross>
  ),

  rhino: () => (
    <Cross y={362} dur={95} delay={30} rev>
      <g className="anim-walk">
        {flip(<g fill="#7b7f86"><ellipse cx="0" cy="-20" rx="34" ry="18" /><path d="M28 -30 q18 0 22 12 q-6 6 -18 4z" /><path d="M46 -22 l6 -12 l2 12z" fill="#e5e7eb" />{[-22, -8, 10, 22].map((x) => <rect key={x} x={x} y="-8" width="8" height="10" />)}</g>)}
      </g>
    </Cross>
  ),

  elephant: () => (
    <Cross y={362} dur={105} delay={50}>
      <g className="anim-walk" fill="#8b8f96">
        <ellipse cx="0" cy="-28" rx="36" ry="24" />
        <circle cx="34" cy="-34" r="15" />
        <path d="M44 -30 q10 16 2 30 l-6 -2 q6 -12 -2 -24z" />
        <path d="M26 -46 q-8 10 2 22 q8 -6 6 -18z" fill="#7b7f86" />
        {[-24, -10, 10, 22].map((x) => <rect key={x} x={x} y="-10" width="10" height="12" />)}
      </g>
    </Cross>
  ),

  tiger: () => (
    <Cross y={366} dur={62} delay={16}>
      <g className="anim-walk">
        <ellipse cx="0" cy="-16" rx="32" ry="12" fill="#f28c28" />
        <circle cx="32" cy="-22" r="10" fill="#f28c28" />
        <path d="M-32 -18 q-18 -6 -22 8" stroke="#f28c28" strokeWidth="4" fill="none" />
        {[-20, -8, 4, 16].map((x) => <path key={x} d={`M${x} -27 l3 10`} stroke="#1f2937" strokeWidth="2.5" />)}
        {[-20, -6, 10, 22].map((x) => <rect key={x} x={x} y="-6" width="6" height="8" fill="#f28c28" />)}
        <circle cx="36" cy="-24" r="1.5" fill="#1f2937" />
      </g>
    </Cross>
  ),

  lion: () => (
    <Cross y={366} dur={76} delay={24} rev>
      <g className="anim-walk">
        {flip(<g><ellipse cx="0" cy="-16" rx="32" ry="12" fill="#d4a15a" /><circle cx="32" cy="-24" r="14" fill="#9a6a2f" /><circle cx="35" cy="-23" r="8" fill="#d4a15a" /><path d="M-32 -18 q-18 -6 -22 8" stroke="#d4a15a" strokeWidth="4" fill="none" />{[-20, -6, 10, 22].map((x) => <rect key={x} x={x} y="-6" width="6" height="8" fill="#d4a15a" />)}</g>)}
      </g>
    </Cross>
  ),

  flamingos: () => (
    <>
      <g>
        {[300, 340, 390, 820, 860].map((x, i) => (
          <g key={x} className={i % 2 ? "anim-bob" : "anim-bob-slow"}>
            <ellipse cx={x} cy="330" rx="12" ry="7" fill="#f9a8d4" />
            <path d={`M${x + 8} 327 q10 -10 2 -22 q-4 -6 4 -8`} stroke="#f9a8d4" strokeWidth="3" fill="none" />
            <path d={`M${x} 337 v18 M${x + 3} 337 v18`} stroke="#f472b6" strokeWidth="1.5" />
          </g>
        ))}
      </g>
      <Cross y={120} dur={50} delay={10}>
        {[0, 30, 60].map((x) => <path key={x} d={`M${x} ${x / 6} q10 -8 20 0 q10 -8 20 0`} stroke="#f472b6" strokeWidth="3" fill="none" />)}
      </Cross>
    </>
  ),

  skier: () => (
    <g transform="translate(0 290)">
      <g className="anim-ski">
        <path d="M-16 6 L18 -2" stroke="#1f2937" strokeWidth="3" />
        <circle cx="0" cy="-24" r="4.5" fill="#dc2626" />
        <path d="M0 -20 L-2 -6 L6 2 M-2 -6 L-8 2 M-1 -16 L-14 -6 M-1 -16 L12 -14" stroke="#2563eb" strokeWidth="3" strokeLinecap="round" />
      </g>
    </g>
  ),

  prayerFlags: () => (
    <g>
      {[[60, 150, 520, 200], [640, 120, 1180, 176]].map(([x1, y1, x2, y2], s) => {
        const n = 14;
        return (
          <g key={s}>
            <path d={`M${x1} ${y1} Q${(x1 + x2) / 2} ${Math.max(y1, y2) + 40} ${x2} ${y2}`} stroke="#6b7280" strokeWidth="1" fill="none" />
            {Array.from({ length: n }, (_, i) => {
              const t = (i + 0.5) / n;
              const cx = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * ((x1 + x2) / 2) + t ** 2 * x2;
              const cy = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * (Math.max(y1, y2) + 40) + t ** 2 * y2;
              return (
                <rect key={i} x={cx - 7} y={cy} width="14" height="16" fill={["#2563eb", "#f8fafc", "#dc2626", "#16a34a", "#facc15"][i % 5]}
                  className="anim-flutter" style={{ transformBox: "fill-box", transformOrigin: "50% 0%", animationDelay: `${-i * 0.2}s` }} />
              );
            })}
          </g>
        );
      })}
    </g>
  ),
};

function Balloon({ colors }: { colors: [string, string] }) {
  return (
    <g>
      <path d="M0 -62 C-42 -62 -46 -12 -14 12 L14 12 C46 -12 42 -62 0 -62z" fill={colors[0]} />
      <path d="M0 -62 C-16 -62 -18 -12 -6 12 L6 12 C18 -12 16 -62 0 -62z" fill={colors[1]} />
      <path d="M-12 12 L-8 26 M12 12 L8 26" stroke="#6b4a2f" strokeWidth="1.2" />
      <rect x="-9" y="26" width="18" height="12" rx="2" fill="#8a5a3c" />
    </g>
  );
}

function Camel({ rider }: { rider: boolean }) {
  return (
    <g fill="#a86b3c">
      <ellipse cx="0" cy="-30" rx="26" ry="11" />
      <path d="M-14 -38 q10 -18 22 0z" />
      <path d="M22 -34 q10 -6 12 -26 q2 -6 10 -4 q4 2 2 8 l-6 2 q-2 16 -12 26z" />
      {[-18, -8, 12, 20].map((x) => <path key={x} d={`M${x} -22 v22`} stroke="#a86b3c" strokeWidth="4" />)}
      {rider && (
        <g>
          <rect x="-8" y="-52" width="10" height="14" fill="#dc2626" />
          <circle cx="-3" cy="-57" r="5" fill="#1f2937" />
          <path d="M-8 -60 h10" stroke="#f59e0b" strokeWidth="4" />
        </g>
      )}
    </g>
  );
}

export const MOTIONS = M;
