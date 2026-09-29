import { useState } from "react";
import type { Link } from "../api/types";
import Confetti from "./Confetti";

// Ticked items are remembered per trip in this browser only.
export default function BookingChecklist({ tripId, items }: { tripId: string; items: Link[] }) {
  const key = `tripwise:checklist:${tripId}`;
  const [done, setDone] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(key) ?? "[]");
    } catch {
      return [];
    }
  });

  const [celebrate, setCelebrate] = useState(0);
  const allDone = done.length === items.length;

  const toggle = (label: string) => {
    const next = done.includes(label) ? done.filter((d) => d !== label) : [...done, label];
    setDone(next);
    if (next.length === items.length && done.length < items.length) setCelebrate((c) => c + 1);
    try {
      localStorage.setItem(key, JSON.stringify(next));
    } catch {
      /* storage unavailable */
    }
  };

  return (
    <div className="card divide-y divide-line">
      {celebrate > 0 && <Confetti key={celebrate} />}
      <div className="px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="font-bold">Book the whole trip</div>
          <div className="text-sm text-muted">
            {done.length}/{items.length} booked
          </div>
        </div>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-paper">
          <div className="h-full rounded-full bg-sea-500 transition-all duration-500" style={{ width: `${(done.length / Math.max(items.length, 1)) * 100}%` }} />
        </div>
        {allDone && <p className="fade-up mt-2 text-sm font-semibold text-sea-700">🎉 All booked. Have an amazing trip!</p>}
      </div>
      {items.map((item, i) => {
        const checked = done.includes(item.label);
        return (
          <label key={item.label} className="flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-paper">
            <input type="checkbox" checked={checked} onChange={() => toggle(item.label)} className="h-4 w-4 accent-sea-600" />
            <span className="w-5 text-xs font-bold text-muted">{i + 1}</span>
            <span className={`flex-1 text-sm ${checked ? "text-muted line-through" : "font-medium"}`}>{item.label}</span>
            <a href={item.url} target="_blank" rel="noreferrer" className="no-print -my-1 rounded-full bg-sea-50 px-3 py-1.5 text-sm font-semibold text-sea-700 ring-1 ring-sea-100 hover:bg-sea-100">
              Open ↗
            </a>
          </label>
        );
      })}
    </div>
  );
}
