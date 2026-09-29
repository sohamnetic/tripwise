// Decorative topographic contour lines, like an old trekking map. Purely visual.
export default function Topo({ className = "", color = "#0d8573" }: { className?: string; color?: string }) {
  const rings = [
    "M300 90c105 0 200 70 200 175s-85 205-200 205-215-70-215-190 105-190 215-190z",
    "M300 135c80 0 150 55 150 135s-65 155-150 155-160-55-160-145 80-145 160-145z",
    "M300 180c55 0 105 38 105 95s-45 110-105 110-110-40-110-100 55-105 110-105z",
    "M302 222c32 0 60 22 60 55s-26 62-60 62-62-22-58-58 26-59 58-59z",
    "M300 258c14 0 26 9 26 22s-11 25-26 25-26-10-26-24 12-23 26-23z",
    "M60 560c60-50 150-70 240-40s170 20 240-30",
    "M20 610c80-60 170-80 270-50s190 30 280-40",
    "M40 40c70 30 120 10 160-30",
    "M520 60c30 40 70 60 110 50",
  ];
  return (
    <svg viewBox="0 0 600 640" className={`pointer-events-none ${className}`} fill="none" aria-hidden="true">
      <g stroke={color} strokeWidth="1.4" strokeLinecap="round">
        {rings.map((d, i) => <path key={i} d={d} opacity={0.35 - i * 0.02} />)}
      </g>
    </svg>
  );
}
