import { useState } from "react";
import type { Plan } from "../api/types";
import { packingList } from "../lib/packing";

// Ticked items are remembered per trip in this browser only.
export default function PackingList({ plan }: { plan: Plan }) {
  const groups = packingList(plan);
  const key = `tripwise:packing:${plan.id}`;
  const [done, setDone] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(key) ?? "[]");
    } catch {
      return [];
    }
  });
  const total = groups.reduce((n, g) => n + g.items.length, 0);

  const toggle = (item: string) => {
    const next = done.includes(item) ? done.filter((d) => d !== item) : [...done, item];
    setDone(next);
    try {
      localStorage.setItem(key, JSON.stringify(next));
    } catch {
      /* storage unavailable */
    }
  };

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div className="font-bold">🎒 Packing list</div>
        <div className="text-sm text-muted">{done.length}/{total} packed</div>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-paper">
        <div className="h-full rounded-full bg-sand-400 transition-all duration-500" style={{ width: `${(done.length / total) * 100}%` }} />
      </div>
      <div className="mt-3 grid gap-4 sm:grid-cols-3">
        {groups.map((g) => (
          <div key={g.title}>
            <div className="mb-1.5 text-xs font-bold uppercase tracking-wide text-muted">{g.title}</div>
            <ul className="space-y-1">
              {g.items.map((item) => {
                const checked = done.includes(item);
                return (
                  <li key={item}>
                    <label className="flex cursor-pointer items-start gap-2 rounded-lg px-1 py-0.5 text-sm hover:bg-paper">
                      <input type="checkbox" checked={checked} onChange={() => toggle(item)} className="mt-0.5 h-4 w-4 shrink-0 accent-sand-600" />
                      <span className={checked ? "text-muted line-through" : ""}>{item}</span>
                    </label>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
