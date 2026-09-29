import type { ReactElement } from "react";
import type { Landmark } from "./types";

// Simple silhouettes of famous places. Each is drawn around (0, 0) = centre of its base,
// growing upwards (negative y). The scene positions and scales them.

const spin = { transformBox: "fill-box", transformOrigin: "50% 50%" } as const;

function Arch({ x, w, h, fill }: { x: number; w: number; h: number; fill: string }) {
  return <path d={`M${x - w / 2} 0 V${-h + w / 2} A${w / 2} ${w / 2} 0 0 1 ${x + w / 2} ${-h + w / 2} V0z`} fill={fill} />;
}

function Flag({ x, y, color = "#f97316" }: { x: number; y: number; color?: string }) {
  return (
    <g>
      <path d={`M${x} ${y} v-26`} stroke="#6b4a2f" strokeWidth="2" />
      <path d={`M${x} ${y - 26} l20 6 l-20 6z`} fill={color} className="anim-flutter" style={{ transformBox: "fill-box", transformOrigin: "0% 50%" }} />
    </g>
  );
}

function Onion({ x, y, w, h, fill }: { x: number; y: number; w: number; h: number; fill: string }) {
  return <path d={`M${x - w / 2} ${y} C${x - w / 2 - w * 0.12} ${y - h * 0.55} ${x - w * 0.2} ${y - h * 0.8} ${x} ${y - h} C${x + w * 0.2} ${y - h * 0.8} ${x + w / 2 + w * 0.12} ${y - h * 0.55} ${x + w / 2} ${y}z`} fill={fill} />;
}

function Spire({ x, w, h, fill, ribs = "#0002" }: { x: number; w: number; h: number; fill: string; ribs?: string }) {
  // curvilinear north-Indian (nagara / rekha) temple tower
  return (
    <g>
      <path d={`M${x - w / 2} 0 V${-h * 0.2} C${x - w / 2 - 4} ${-h * 0.62} ${x - w * 0.3} ${-h * 0.9} ${x} ${-h} C${x + w * 0.3} ${-h * 0.9} ${x + w / 2 + 4} ${-h * 0.62} ${x + w / 2} ${-h * 0.2} V0z`} fill={fill} />
      <path d={`M${x - w / 4} 0 V${-h * 0.2} C${x - w / 4} ${-h * 0.6} ${x - w * 0.12} ${-h * 0.88} ${x} ${-h} M${x + w / 4} 0 V${-h * 0.2} C${x + w / 4} ${-h * 0.6} ${x + w * 0.12} ${-h * 0.88} ${x} ${-h}`} stroke={ribs} strokeWidth="2" fill="none" />
      {[0.25, 0.45, 0.65].map((f) => <path key={f} d={`M${x - w / 2 + 2} ${-h * f} h${w - 4}`} stroke={ribs} strokeWidth="1.5" />)}
      <ellipse cx={x} cy={-h - 3} rx={w * 0.22} ry="5" fill={fill} stroke={ribs} />
      <circle cx={x} cy={-h - 11} r="4" fill="#e0b13c" />
    </g>
  );
}

function Chorten({ x, s = 1 }: { x: number; s?: number }) {
  return (
    <g transform={`translate(${x} 0) scale(${s})`}>
      <rect x="-16" y="-14" width="32" height="14" fill="#f5f1e8" />
      <rect x="-11" y="-22" width="22" height="8" fill="#ece6d8" />
      <path d="M-12 -22 q12 -26 24 0z" fill="#f5f1e8" />
      <path d="M-3 -38 h6 l-1 -18 h-4z" fill="#e0b13c" />
    </g>
  );
}

const L: Record<Landmark, () => ReactElement> = {
  taj: () => (
    <g>
      <rect x="-165" y="-14" width="330" height="14" fill="#e9e2d2" />
      {[-140, 140].map((x) => (
        <g key={x}>
          <rect x={x - 5} y="-150" width="10" height="136" fill="#f7f3ea" />
          {[-60, -100].map((y) => <rect key={y} x={x - 8} y={y} width="16" height="4" fill="#e9e2d2" />)}
          <rect x={x - 9} y="-155" width="18" height="6" fill="#e9e2d2" />
          <path d={`M${x - 8} -155 q8 -20 16 0z`} fill="#f7f3ea" />
        </g>
      ))}
      <rect x="-82" y="-102" width="164" height="88" fill="#faf6ee" />
      <path d="M-26 -14 V-72 q26 -30 52 0 V-14z" fill="#e3dac6" />
      {[-58, 58].map((x) => <path key={x} d={`M${x - 10} -30 v-26 q10 -14 20 0 v26z`} fill="#e3dac6" />)}
      {[-60, 60].map((x) => (
        <g key={x}>
          <rect x={x - 12} y="-114" width="24" height="12" fill="#efe9dc" />
          <Onion x={x} y={-114} w={22} h={18} fill="#fbf8f1" />
        </g>
      ))}
      <rect x="-42" y="-110" width="84" height="8" fill="#efe9dc" />
      <Onion x={0} y={-110} w={92} h={74} fill="#fcf9f3" />
      <path d="M0 -184 v-18" stroke="#d4b25f" strokeWidth="3" />
    </g>
  ),

  hawaMahal: () => {
    const tiers: [number, number, number][] = [[132, -60, 60], [112, -100, 40], [88, -134, 34], [62, -162, 28], [36, -184, 22]];
    return (
      <g>
        {tiers.map(([hw, top, h], i) => (
          <g key={i}>
            <rect x={-hw} y={top} width={hw * 2} height={h} fill="#e3808c" />
            {Array.from({ length: Math.floor((hw * 2 - 8) / 16) }, (_, k) => (
              <g key={k}>
                <rect x={-hw + 6 + k * 16} y={top + 5} width="9" height={h - 12} rx="4.5" fill="#fbe0e4" />
                <rect x={-hw + 4 + k * 16} y={top} width="13" height="3" fill="#c95f6d" />
              </g>
            ))}
            {Array.from({ length: Math.floor(hw / 18) + 1 }, (_, k) => (
              <circle key={k} cx={-hw + 8 + k * ((hw * 2 - 16) / Math.max(1, Math.floor(hw / 18)))} cy={top - 3} r="5" fill="#e3808c" />
            ))}
          </g>
        ))}
        <path d="M-10 -188 q10 -18 20 0z" fill="#e3808c" />
      </g>
    );
  },

  indiaGate: () => (
    <g>
      <path d="M-62 0 V-165 H62 V0 H30 V-95 A30 30 0 0 0 -30 -95 V0z" fill="#d9a877" />
      <rect x="-70" y="-182" width="140" height="17" fill="#c9965f" />
      <rect x="-50" y="-198" width="100" height="16" fill="#d9a877" />
      <ellipse cx="0" cy="-199" rx="24" ry="8" fill="#c9965f" />
      <circle cx="0" cy="-6" r="5" fill="#f97316" className="anim-glow" />
    </g>
  ),

  gateway: () => (
    <g>
      <rect x="-120" y="-108" width="240" height="108" fill="#d8b784" />
      <Arch x={0} w={70} h={92} fill="#a98659" />
      {[-82, 82].map((x) => <Arch key={x} x={x} w={32} h={56} fill="#a98659" />)}
      <rect x="-120" y="-118" width="240" height="10" fill="#c6a36d" />
      {[-110, -58, 58, 110].map((x) => (
        <g key={x}>
          <rect x={x - 12} y="-150" width="24" height="32" fill="#d8b784" />
          <Onion x={x} y={-150} w={24} h={20} fill="#c6a36d" />
        </g>
      ))}
    </g>
  ),

  howrah: () => {
    const top = (x: number) => (Math.abs(x) >= 120 ? -150 + ((Math.abs(x) - 120) * 110) / 200 : -150 + ((120 - Math.abs(x)) * 90) / 120);
    return (
      <g stroke="#6f8196" fill="none">
        <path d="M-320 -40 L-120 -150 L0 -60 L120 -150 L320 -40" strokeWidth="6" />
        {Array.from({ length: 22 }, (_, i) => {
          const x = -315 + i * 30;
          return <path key={i} d={`M${x} -42 L${x + 15} ${top(x + 15)}`} strokeWidth="2" />;
        })}
        {[-120, 120].map((x) => <path key={x} d={`M${x - 14} 0 L${x - 6} -152 M${x + 14} 0 L${x + 6} -152`} strokeWidth="5" />)}
        <rect x="-330" y="-46" width="660" height="8" fill="#6f8196" stroke="none" />
      </g>
    );
  },

  charminar: () => (
    <g>
      <rect x="-72" y="-118" width="144" height="118" fill="#e3cfa8" />
      <Arch x={0} w={78} h={96} fill="#b99a68" />
      <rect x="-76" y="-134" width="152" height="16" fill="#cbb183" />
      {Array.from({ length: 8 }, (_, i) => <rect key={i} x={-66 + i * 17} y="-131" width="9" height="10" rx="4" fill="#b99a68" />)}
      {[-72, 72].map((x) => (
        <g key={x}>
          <rect x={x - 10} y="-205" width="20" height="205" fill="#e3cfa8" />
          {[-60, -120, -170].map((y) => <rect key={y} x={x - 13} y={y} width="26" height="6" fill="#cbb183" />)}
          <Onion x={x} y={-205} w={22} h={22} fill="#cbb183" />
        </g>
      ))}
    </g>
  ),

  goldenTemple: () => (
    <g>
      <rect x="-320" y="-16" width="240" height="8" fill="#f4efe4" />
      <rect x="-82" y="-42" width="164" height="42" fill="#f4efe4" />
      {Array.from({ length: 6 }, (_, i) => <Arch key={i} x={-68 + i * 27} w={14} h={30} fill="#c9b99a" />)}
      <rect x="-72" y="-84" width="144" height="42" fill="#e5b53a" />
      {Array.from({ length: 5 }, (_, i) => <rect key={i} x={-60 + i * 26} y="-76" width="12" height="24" rx="6" fill="#c9951f" />)}
      {[-62, 62].map((x) => <Onion key={x} x={x} y={-84} w={18} h={20} fill="#e5b53a" />)}
      <Onion x={0} y={-84} w={78} h={66} fill="#f0c24a" />
      <path d="M0 -150 v-14" stroke="#c9951f" strokeWidth="3" />
    </g>
  ),

  lakePalace: () => (
    <g>
      <rect x="-165" y="-46" width="330" height="46" fill="#f6f1e6" />
      {Array.from({ length: 12 }, (_, i) => <Arch key={i} x={-148 + i * 27} w={14} h={30} fill="#d6ccb8" />)}
      <rect x="-120" y="-82" width="240" height="36" fill="#efe8da" />
      {Array.from({ length: 8 }, (_, i) => <Arch key={i} x={-100 + i * 28.5} w={12} h={24} fill="#d6ccb8" />)}
      {[-150, -100, 100, 150].map((x) => (
        <g key={x}>
          <rect x={x - 2} y="-62" width="4" height="16" fill="#e4dccb" />
          <Onion x={x} y={-62} w={20} h={14} fill="#f6f1e6" />
        </g>
      ))}
      <Onion x={0} y={-82} w={60} h={40} fill="#f6f1e6" />
    </g>
  ),

  blueFort: () => <Fort hill="#a8805c" wall="#b5744c" houses={["#5b8fd8", "#7aa6e6", "#4a7cc4"]} />,
  goldenFort: () => <Fort hill="#d9a45a" wall="#e2b35f" houses={["#e8c07a", "#d9aa62"]} />,
  ruinFort: () => <Fort hill="#8f7a5a" wall="#9c7f5f" houses={[]} />,

  palace: () => (
    <g>
      <rect x="-175" y="-70" width="350" height="70" fill="#f0e2c4" />
      {Array.from({ length: 13 }, (_, i) => <Arch key={i} x={-156 + i * 26} w={14} h={34} fill="#cdb98f" />)}
      <rect x="-42" y="-132" width="84" height="62" fill="#f0e2c4" />
      <Onion x={0} y={-132} w={64} h={56} fill="#d98a6a" />
      {[-125, 125].map((x) => (
        <g key={x}>
          <rect x={x - 22} y="-100" width="44" height="30" fill="#f0e2c4" />
          <Onion x={x} y={-100} w={34} h={30} fill="#d98a6a" />
        </g>
      ))}
      {/* festival lights */}
      <g fill="#ffd766">
        {Array.from({ length: 22 }, (_, i) => <circle key={i} cx={-170 + i * 16} cy="-72" r="2" className={i % 2 ? "anim-twinkle" : "anim-twinkle-slow"} />)}
        {Array.from({ length: 8 }, (_, i) => <circle key={`c${i}`} cx={-30 + i * 8.5} cy="-134" r="1.8" className="anim-twinkle" />)}
      </g>
    </g>
  ),

  gopuram: () => (
    <g>
      <rect x="-82" y="-24" width="164" height="24" fill="#c98a3c" />
      <Arch x={0} w={34} h={24} fill="#6b3a1f" />
      {Array.from({ length: 7 }, (_, i) => {
        const hw = 72 - i * 8;
        const y = -24 - (i + 1) * 21;
        return (
          <g key={i}>
            <rect x={-hw} y={y} width={hw * 2} height="21" fill={i % 2 ? "#d9a14a" : "#e2b05d"} />
            {Array.from({ length: Math.floor(hw / 14) }, (_, k) => (
              <rect key={k} x={-hw + 8 + k * 28} y={y + 5} width="9" height="11" fill={k % 2 ? "#b5463a" : "#3f7d8a"} opacity="0.8" />
            ))}
          </g>
        );
      })}
      <path d="M-26 -171 q26 -34 52 0z" fill="#e2b05d" />
      {[-16, 0, 16].map((x) => <circle key={x} cx={x} cy={-190 + (x === 0 ? -4 : 6)} r="3.5" fill="#e0b13c" />)}
    </g>
  ),

  kalinga: () => (
    <g>
      <path d="M-130 0 V-40 L-108 -84 L-62 -84 L-40 -40 V0z" fill="#e6dccb" />
      <Spire x={10} w={96} h={200} fill="#efe6d6" />
      <Flag x={10} y={-214} color="#dc2626" />
    </g>
  ),

  sunTemple: () => (
    <g>
      <rect x="-160" y="-62" width="320" height="62" fill="#b08a6a" />
      <rect x="-160" y="-40" width="320" height="6" fill="#9a765a" />
      <path d="M-120 -62 L-80 -120 L-60 -120 L-40 -150 L40 -150 L60 -120 L80 -120 L120 -62z" fill="#a67f60" />
      <path d="M-40 -150 L-20 -176 H20 L40 -150z" fill="#9a765a" />
      {[-90, 90].map((x) => (
        <g key={x} transform={`translate(${x} -30)`}>
          <g className="anim-spin-slow" style={spin}>
            <circle r="26" fill="none" stroke="#6e4f37" strokeWidth="5" />
            {Array.from({ length: 8 }, (_, i) => (
              <path key={i} d={`M0 0 L${26 * Math.cos((i * Math.PI) / 4)} ${26 * Math.sin((i * Math.PI) / 4)}`} stroke="#6e4f37" strokeWidth="3" />
            ))}
            <circle r="6" fill="#6e4f37" />
          </g>
        </g>
      ))}
    </g>
  ),

  monastery: () => (
    <g>
      <path d="M-230 0 C-180 -40 -130 -110 -40 -120 C40 -125 150 -90 230 0z" fill="#b89a78" />
      {[[-110, -150, 110, 40], [-80, -190, 80, 40], [-40, -222, 50, 32]].map(([x, y, w, h], i) => (
        <g key={i}>
          <rect x={x} y={y} width={w + (i === 2 ? 30 : 60)} height={h} fill="#f3efe6" />
          <rect x={x} y={y} width={w + (i === 2 ? 30 : 60)} height="7" fill="#8c2f39" />
          {Array.from({ length: 5 }, (_, k) => <rect key={k} x={x + 10 + k * 22} y={y + 16} width="7" height="10" fill="#3b2f2f" />)}
        </g>
      ))}
      <path d="M-44 -222 L-30 -238 H24 L38 -222z" fill="#e0b13c" />
      <Chorten x={140} s={1.2} />
      <Chorten x={175} s={0.9} />
    </g>
  ),

  jhula: () => (
    <g>
      <path d="M-320 -34 Q-230 -44 -120 -120 Q0 -44 120 -120 Q230 -44 320 -34" stroke="#6b7280" strokeWidth="3" fill="none" />
      {Array.from({ length: 21 }, (_, i) => {
        const x = -300 + i * 30;
        return <path key={i} d={`M${x} -34 V${cableY(x)}`} stroke="#9ca3af" strokeWidth="1.5" />;
      })}
      <rect x="-330" y="-36" width="660" height="6" fill="#d6d3cd" />
      {[-120, 120].map((x) => (
        <g key={x}>
          <path d={`M${x - 16} 0 V-120 H${x + 16} V0 H${x + 8} V-70 A8 8 0 0 0 ${x - 8} -70 V0z`} fill="#e07a3f" />
          <path d={`M${x - 20} -120 h40 l-6 -10 h-28z`} fill="#c65f2a" />
        </g>
      ))}
    </g>
  ),

  lighthouse: () => (
    <g>
      <path d="M-20 0 L-12 -170 H12 L20 0z" fill="#f8fafc" />
      {[0, 1, 2].map((i) => <path key={i} d={`M${-19 + i * 1.5} ${-20 - i * 55} L${-17.5 + i * 1.5} ${-48 - i * 55} H${17.5 - i * 1.5} L${19 - i * 1.5} ${-20 - i * 55}z`} fill="#dc2626" />)}
      <rect x="-15" y="-176" width="30" height="6" fill="#374151" />
      <rect x="-11" y="-196" width="22" height="20" fill="#fde68a" className="anim-glow" />
      <path d="M-14 -196 L0 -212 L14 -196z" fill="#374151" />
      {/* sweeping beam: apex at the lamp (left-middle of its box) */}
      <polygon points="0,-186 360,-222 360,-150" fill="#fff7c2" opacity="0.35" className="anim-sweep" style={{ transformBox: "fill-box", transformOrigin: "0% 50%" }} />
    </g>
  ),

  shoreTemple: () => (
    <g>
      <rect x="-140" y="-18" width="280" height="18" fill="#8a8171" />
      {[[-60, 26, 110], [40, 34, 160]].map(([x, hw, h]) => (
        <g key={x}>
          {Array.from({ length: 6 }, (_, i) => (
            <rect key={i} x={x - hw + i * (hw / 7)} y={-18 - (i + 1) * (h / 6)} width={(hw - i * (hw / 7)) * 2} height={h / 6} fill={i % 2 ? "#a39a8a" : "#b1a896"} />
          ))}
          <path d={`M${x - 8} ${-18 - h} q8 -16 16 0z`} fill="#a39a8a" />
        </g>
      ))}
    </g>
  ),

  mahabodhi: () => (
    <g>
      <rect x="-80" y="-30" width="160" height="30" fill="#c29a60" />
      <path d="M-42 -30 L-26 -210 H26 L42 -30z" fill="#d1ab70" />
      {Array.from({ length: 9 }, (_, i) => <path key={i} d={`M${-40 + i * 1.7} ${-50 - i * 18} h${80 - i * 3.4}`} stroke="#a7834f" strokeWidth="2" />)}
      {Array.from({ length: 6 }, (_, i) => <rect key={i} x="-5" y={-70 - i * 24} width="10" height="12" rx="5" fill="#8a6a3c" />)}
      <ellipse cx="0" cy="-213" rx="18" ry="6" fill="#c29a60" />
      <path d="M-5 -218 L0 -240 L5 -218z" fill="#e0b13c" />
      {[-62, 62].map((x) => <path key={x} d={`M${x - 12} -30 L${x - 7} -90 H${x + 7} L${x + 12} -30z`} fill="#c9a36a" />)}
    </g>
  ),

  khajuraho: () => (
    <g>
      <rect x="-170" y="-20" width="340" height="20" fill="#c49160" />
      <Spire x={-95} w={64} h={120} fill="#d6a86f" />
      <Spire x={95} w={58} h={105} fill="#d6a86f" />
      <Spire x={-30} w={70} h={150} fill="#dcb07a" />
      <Spire x={30} w={84} h={190} fill="#e0b683" />
    </g>
  ),

  nagara: () => (
    <g>
      <rect x="-150" y="-24" width="300" height="24" fill="#d9a877" />
      <path d="M-140 -24 V-60 L-120 -96 H-70 L-50 -60 V-24z" fill="#e6b98a" />
      <path d="M140 -24 V-60 L120 -96 H70 L50 -60 V-24z" fill="#e6b98a" />
      <Spire x={0} w={90} h={200} fill="#ecc095" />
      <Flag x={0} y={-214} />
    </g>
  ),

  rockMemorial: () => (
    <g>
      <path d="M-150 6 C-130 -36 -70 -58 0 -54 C70 -60 125 -36 160 6z" fill="#6b6254" />
      <rect x="-52" y="-102" width="104" height="50" fill="#d9cbb5" />
      {Array.from({ length: 4 }, (_, i) => <Arch key={i} x={-36 + i * 24} w={12} h={30} fill="#9c8e76" />)}
      <path d="M-40 -102 q40 -44 80 0z" fill="#cbbb9f" />
      <path d="M0 -146 v-12" stroke="#8a7a60" strokeWidth="3" />
      <path d="M220 6 C220 -20 250 -30 270 -20 C290 -10 300 0 300 6z" fill="#6b6254" />
      <path d="M252 -22 v-70 h10 v70z M246 -92 h22 v-14 h-22z" fill="#8a8171" />
    </g>
  ),

  church: () => (
    <g>
      <rect x="-90" y="-72" width="150" height="72" fill="#f2d27a" />
      <path d="M-98 -72 L-15 -118 L68 -72z" fill="#b45f3c" />
      {[-66, -36, -6, 24].map((x) => <Arch key={x} x={x} w={12} h={40} fill="#7c6a4a" />)}
      <rect x="40" y="-160" width="44" height="160" fill="#f2d27a" />
      <rect x="40" y="-160" width="44" height="6" fill="#fff" />
      <circle cx="62" cy="-126" r="10" fill="#fff" stroke="#7c6a4a" strokeWidth="2" />
      <path d="M62 -126 l0 -6 M62 -126 l4 2" stroke="#374151" strokeWidth="1.5" />
      <path d="M36 -160 L62 -214 L88 -160z" fill="#b45f3c" />
      <path d="M62 -214 v-14 M56 -222 h12" stroke="#7c6a4a" strokeWidth="2" />
    </g>
  ),

  hillTown: () => {
    const houses: [number, number, string, string][] = [
      [-200, -30, "#f4a261", "#9c4f2e"], [-150, -58, "#e9c46a", "#8a5a3c"], [-95, -86, "#8ecae6", "#335c81"],
      [-40, -104, "#f7f7f2", "#b45f3c"], [20, -96, "#e76f51", "#6b2e1f"], [80, -74, "#ffd6a5", "#9c4f2e"],
      [140, -48, "#bde0fe", "#335c81"], [-120, -22, "#fefae0", "#8a5a3c"], [60, -30, "#f4a261", "#6b2e1f"],
    ];
    return (
      <g>
        <path d="M-260 0 C-180 -60 -110 -120 -20 -128 C70 -130 170 -80 260 0z" fill="#5f8f5a" />
        {houses.map(([x, y, wall, roof], i) => (
          <g key={i}>
            <rect x={x} y={y - 22} width="36" height="22" fill={wall} />
            <path d={`M${x - 4} ${y - 22} L${x + 18} ${y - 38} L${x + 40} ${y - 22}z`} fill={roof} />
            <rect x={x + 8} y={y - 16} width="7" height="8" fill="#374151" opacity="0.6" />
          </g>
        ))}
        {[-240, -180, 200, 235].map((x, i) => <path key={x} d={`M${x} ${-10 - i * 4} l14 -48 l14 48z`} fill="#2f5d3a" />)}
      </g>
    );
  },

  ghats: () => {
    const b: [number, number, number, string][] = [
      [-300, 70, 60, "#e8c9a0"], [-235, 100, 50, "#d9a877"], [-180, 60, 70, "#f0d9b5"], [-105, 120, 46, "#e3b98c"],
      [-55, 80, 60, "#f2e3c9"], [10, 140, 55, "#d9a877"], [70, 90, 60, "#ecd2ad"], [135, 110, 48, "#e3b98c"],
      [188, 70, 62, "#f0d9b5"], [255, 96, 60, "#d9a877"],
    ];
    return (
      <g>
        {b.map(([x, h, w, c], i) => (
          <g key={i}>
            <rect x={x} y={-h} width={w} height={h} fill={c} />
            {Array.from({ length: Math.floor(h / 26) }, (_, r) => (
              <rect key={r} x={x + 8} y={-h + 10 + r * 26} width={w - 16} height="8" fill="#0003" />
            ))}
            {i % 3 === 1 && <Spire x={x + w / 2} w={w * 0.6} h={60} fill={c} />}
            {i % 3 === 2 && <path d={`M${x + 6} ${-h} q${w / 2 - 6} -22 ${w - 12} 0z`} fill="#c65f2a" />}
          </g>
        ))}
        {[0, 1, 2, 3].map((i) => <rect key={i} x="-320" y={-8 + i * 8 - 16} width="640" height="8" fill={i % 2 ? "#b8956a" : "#c9a67a"} />)}
        {[-260, -120, 60, 220].map((x) => (
          <g key={x}>
            <path d={`M${x} -20 v-30`} stroke="#6b4a2f" strokeWidth="2" />
            <path d={`M${x - 20} -48 q20 -16 40 0z`} fill="#e9c46a" />
          </g>
        ))}
      </g>
    );
  },

  chineseNets: () => (
    <g>
      <rect x="-300" y="-10" width="600" height="10" fill="#6b4a2f" />
      {[-160, 40, 220].map((x, i) => (
        <g key={x} transform={`translate(${x} -8)`}>
          <g className="anim-dip" style={{ transformBox: "fill-box", transformOrigin: "100% 100%", animationDelay: `${-i * 1.3}s` }}>
            <path d="M0 0 L-150 -118 M-6 0 L-120 -130" stroke="#5b3a29" strokeWidth="4" />
            <path d="M-150 -118 L-190 -40 L-80 -48z" fill="none" stroke="#5b3a29" strokeWidth="1.5" />
            <path d="M-190 -40 Q-135 -10 -80 -48" fill="#8a7a5a" opacity="0.35" stroke="#5b3a29" strokeWidth="1" />
            {Array.from({ length: 5 }, (_, k) => <path key={k} d={`M${-182 + k * 22} -44 L${-150 + k * 14} -114`} stroke="#5b3a29" strokeWidth="0.8" opacity="0.6" />)}
          </g>
          {[0, 1, 2].map((k) => <circle key={k} cx={6 + k * 8} cy={-4 - k * 6} r="5" fill="#8a8171" />)}
        </g>
      ))}
    </g>
  ),

  waterfall: () => (
    <g>
      <path d="M-240 0 C-236 -70 -232 -130 -196 -160 C-150 -192 -80 -192 -20 -186 V0z" fill="#5b6f5f" />
      <path d="M40 0 V-186 C100 -192 170 -186 212 -160 C244 -138 250 -70 252 0z" fill="#5b6f5f" />
      <g stroke="#4a5d4f" strokeWidth="3" fill="none" strokeLinecap="round">
        <path d="M-200 -120 q30 -10 60 4 M-160 -70 q40 -8 80 6 M-110 -150 q30 -8 60 0 M80 -140 q40 -8 90 6 M100 -80 q40 -6 90 8" />
      </g>
      <g fill="#2f6b45">
        {[-220, -170, -110, -60, 80, 140, 200].map((x, i) => <ellipse key={x} cx={x} cy={-184 - (i % 2) * 10} rx="34" ry="20" />)}
      </g>
      <rect x="-20" y="-186" width="60" height="186" fill="#cfe7f2" />
      <g stroke="#ffffff" strokeWidth="4" strokeLinecap="round" fill="none" opacity="0.9">
        {[-12, 0, 12, 24, 34].map((x, i) => (
          <path key={x} d={`M${x} -186 V0`} strokeDasharray="18 12" className="anim-cascade" style={{ animationDelay: `${-i * 0.2}s` }} />
        ))}
      </g>
      <ellipse cx="10" cy="-4" rx="70" ry="14" fill="#fff" opacity="0.6" className="anim-glow" />
    </g>
  ),

  caves: () => (
    <g>
      <path d="M-280 0 V-120 C-200 -170 -80 -180 40 -176 C160 -172 240 -150 280 -110 V0z" fill="#b08968" />
      <path d="M-280 -118 C-200 -150 -80 -160 40 -156 C160 -152 240 -134 280 -104" stroke="#9a7456" strokeWidth="6" fill="none" />
      {[-220, -150, -80, -10, 60, 130, 200].map((x, i) => (
        <g key={x}>
          <Arch x={x} w={40} h={i % 2 ? 70 : 80} fill="#3b2a20" />
          <rect x={x - 26} y={-4 - (i % 2 ? 74 : 84)} width="6" height={i % 2 ? 74 : 84} fill="#c29a78" />
        </g>
      ))}
      {[-190, -40, 110].map((x) => <Arch key={x} x={x} w={26} h={40} fill="#3b2a20" />)}
    </g>
  ),

  pagoda: () => (
    <g>
      <rect x="-50" y="-60" width="100" height="60" fill="#8a5a3c" />
      <Arch x={0} w={22} h={40} fill="#3b2a20" />
      {[0, 1, 2, 3].map((i) => (
        <path key={i} d={`M${-78 + i * 14} ${-60 - i * 34} L${-42 + i * 10} ${-92 - i * 34} H${42 - i * 10} L${78 - i * 14} ${-60 - i * 34}z`} fill={i % 2 ? "#6f4328" : "#7a4a2a"} />
      ))}
      <path d="M-12 -196 L0 -232 L12 -196z" fill="#6f4328" />
      <circle cx="0" cy="-236" r="5" fill="#e0b13c" />
      {[-150, -115, 115, 150].map((x, i) => <path key={x} d={`M${x} 0 l18 ${-110 - (i % 2) * 30} l18 ${110 + (i % 2) * 30}z`} fill="#2f5d3a" />)}
    </g>
  ),

  houseboats: () => (
    <g>
      {[-190, 0, 190].map((x, i) => (
        <g key={x} transform={`translate(${x} ${i === 1 ? 4 : 0})`}>
          <path d="M-80 0 h160 l-10 12 h-140z" fill="#5b3a29" />
          <rect x="-70" y="-38" width="140" height="38" fill={["#a0522d", "#8b5e3c", "#9c6b3f"][i]} />
          {Array.from({ length: 6 }, (_, k) => <rect key={k} x={-62 + k * 22} y="-30" width="12" height="16" fill="#fde68a" opacity="0.85" />)}
          <path d="M-78 -38 L-60 -56 H60 L78 -38z" fill="#6b3a1f" />
        </g>
      ))}
    </g>
  ),

  burj: () => (
    <g>
      <path d="M-34 0 L-26 -120 L-18 -120 L-14 -210 L-8 -210 L-5 -290 L-2 -290 L0 -340 L2 -290 L5 -290 L8 -210 L14 -210 L18 -120 L26 -120 L34 0z" fill="#9fb8d6" />
      <path d="M0 -340 V0" stroke="#dbe6f3" strokeWidth="2" />
      {Array.from({ length: 10 }, (_, i) => <circle key={i} cx={(i % 2 ? 4 : -4)} cy={-30 - i * 28} r="1.6" fill="#fde68a" className="anim-twinkle" />)}
    </g>
  ),

  marinaBay: () => (
    <g>
      {[-90, 0, 90].map((x) => (
        <g key={x}>
          <path d={`M${x - 22} 0 L${x - 16} -170 H${x + 16} L${x + 22} 0z`} fill="#cfd8e3" />
          {Array.from({ length: 12 }, (_, k) => <rect key={k} x={x - 10} y={-160 + k * 13} width="20" height="4" fill="#fde68a" opacity="0.7" />)}
        </g>
      ))}
      <path d="M-140 -176 Q0 -190 150 -176 L140 -168 Q0 -180 -130 -168z" fill="#e5ebf2" />
    </g>
  ),

  prang: () => (
    <g>
      <rect x="-150" y="-20" width="300" height="20" fill="#d9ccb4" />
      {[[-100, 22, 90], [100, 22, 90], [0, 34, 190]].map(([x, hw, h]) => (
        <g key={x}>
          {Array.from({ length: 7 }, (_, i) => (
            <path key={i} d={`M${x - hw + i * (hw / 8)} ${-20 - i * (h / 7)} q${hw - i * (hw / 8)} ${-h / 10} ${(hw - i * (hw / 8)) * 2} 0 v${-h / 7 + 2} h${-(hw - i * (hw / 8)) * 2}z`} fill={i % 2 ? "#e7dccb" : "#f1e8d8"} />
          ))}
          <path d={`M${x - 3} ${-20 - h} L${x} ${-40 - h} L${x + 3} ${-20 - h}z`} fill="#a39a8a" />
        </g>
      ))}
    </g>
  ),

  splitGate: () => (
    <g>
      {[-1, 1].map((side) => (
        <g key={side}>
          {Array.from({ length: 7 }, (_, i) => {
            const w = 60 - i * 7;
            const x = side < 0 ? -18 - w : 18;
            return <rect key={i} x={x} y={-24 - i * 24} width={w} height="24" fill={i % 2 ? "#6f5a4a" : "#7d6754"} />;
          })}
        </g>
      ))}
      <rect x="-90" y="-24" width="180" height="24" fill="#5f4b3c" />
      <rect x="-18" y="-24" width="36" height="24" fill="#3b2a20" />
    </g>
  ),

  stupa: () => (
    <g>
      <rect x="-150" y="-24" width="300" height="24" fill="#f3efe6" />
      <path d="M-120 -24 Q-120 -110 0 -112 Q120 -110 120 -24z" fill="#f8f5ee" />
      <rect x="-24" y="-142" width="48" height="30" fill="#e0b13c" />
      <g fill="#1f2937">
        <path d="M-17 -128 q7 -6 14 0 q-7 4 -14 0z M3 -128 q7 -6 14 0 q-7 4 -14 0z" />
        <path d="M0 -122 q-3 6 0 8" stroke="#1f2937" strokeWidth="2" fill="none" />
      </g>
      <path d="M-20 -142 L-6 -210 H6 L20 -142z" fill="#e0b13c" />
      {Array.from({ length: 8 }, (_, i) => <path key={i} d={`M${-18 + i * 1.6} ${-146 - i * 8} h${36 - i * 3.2}`} stroke="#c9951f" strokeWidth="1.5" />)}
      <path d="M-10 -210 q10 -12 20 0z" fill="#e0b13c" />
    </g>
  ),

  waterVillas: () => (
    <g>
      <path d="M-320 -16 H320" stroke="#b08a66" strokeWidth="5" />
      {[-240, -120, 0, 120, 240].map((x) => (
        <g key={x}>
          {[-24, 24].map((d) => <path key={d} d={`M${x + d} 0 V-16`} stroke="#8a6a4a" strokeWidth="3" />)}
          <rect x={x - 32} y="-40" width="64" height="24" fill="#f3e6cc" />
          <rect x={x - 8} y="-34" width="16" height="18" fill="#8a6a4a" />
          <path d={`M${x - 42} -40 L${x} -70 L${x + 42} -40z`} fill="#c9a063" />
        </g>
      ))}
    </g>
  ),
};

// y of the Laxman Jhula cable at x: a quadratic curve between the towers, roughly straight outside them
function cableY(x: number) {
  const ax = Math.abs(x);
  if (ax >= 120) return -120 + ((ax - 120) / 200) * 86;
  const t = (x + 120) / 240;
  return (1 - t) ** 2 * -120 + 2 * (1 - t) * t * -44 + t ** 2 * -120;
}

function Fort({ hill, wall, houses }: { hill: string; wall: string; houses: string[] }) {
  return (
    <g>
      <path d="M-270 0 C-210 -60 -160 -120 -60 -132 C40 -142 150 -110 270 0z" fill={hill} />
      <rect x="-120" y="-196" width="240" height="66" fill={wall} />
      {Array.from({ length: 16 }, (_, i) => <rect key={i} x={-120 + i * 15} y="-204" width="9" height="8" fill={wall} />)}
      {[-120, -40, 40, 120].map((x) => <rect key={x} x={x - 14} y="-214" width="28" height="84" rx="10" fill={wall} />)}
      {Array.from({ length: 8 }, (_, i) => <rect key={i} x={-100 + i * 26} y="-176" width="8" height="12" fill="#0004" />)}
      {houses.length > 0 &&
        Array.from({ length: 18 }, (_, i) => (
          <rect key={i} x={-250 + i * 28} y={-18 - ((i * 7) % 3) * 8} width="22" height={18 + ((i * 5) % 3) * 6} fill={houses[i % houses.length]} />
        ))}
    </g>
  );
}

export const LANDMARKS = L;
