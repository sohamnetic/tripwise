import type { BudgetKey, BudgetLine } from "../api/types";
import { rupees } from "../lib/format";

const COLORS: Record<BudgetKey, string> = {
  transport: "#0d8573",
  stay: "#2f7fd8",
  food: "#f5b544",
  activities: "#f06a4f",
  local: "#6d5bd0",
  buffer: "#cbd5e1",
};

// Donut of where the money goes; the buffer slice shows what's kept aside.
export default function BudgetBreakdown({ lines, budget }: { lines: BudgetLine[]; budget: number }) {
  const parts = lines.map((l) => ({ ...l, value: l.key === "buffer" ? Math.max(0, budget - lines.reduce((s, x) => s + x.spent, 0)) : l.spent }));
  const total = parts.reduce((s, p) => s + p.value, 0) || 1;
  const R = 60;
  const C = 2 * Math.PI * R;
  let offset = 0;

  return (
    <div className="grid items-center gap-6 sm:grid-cols-[180px_1fr]">
      <svg viewBox="0 0 160 160" className="mx-auto w-40" role="img" aria-label="Budget breakdown">
        <circle cx="80" cy="80" r={R} fill="none" stroke="#f1f5f9" strokeWidth="22" />
        {parts.map((p) => {
          const len = (p.value / total) * C;
          const el = (
            <circle key={p.key} cx="80" cy="80" r={R} fill="none" stroke={COLORS[p.key]} strokeWidth="22"
              strokeDasharray={`${Math.max(len - 1.5, 0)} ${C}`} strokeDashoffset={-offset} transform="rotate(-90 80 80)" />
          );
          offset += len;
          return el;
        })}
        <text x="80" y="76" textAnchor="middle" className="fill-muted text-[10px] font-semibold">BUDGET</text>
        <text x="80" y="94" textAnchor="middle" className="fill-ink text-[15px] font-extrabold">{rupees(budget)}</text>
      </svg>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-muted">
            <th className="pb-2 font-semibold">Category</th>
            <th className="pb-2 text-right font-semibold">Planned</th>
            <th className="pb-2 text-right font-semibold">Spent</th>
          </tr>
        </thead>
        <tbody>
          {parts.map((p) => (
            <tr key={p.key} className="border-t border-line">
              <td className="py-2">
                <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full" style={{ background: COLORS[p.key] }} />
                {p.label}
              </td>
              <td className="py-2 text-right text-muted">{rupees(p.allocated)}</td>
              <td className="py-2 text-right font-semibold">{p.key === "buffer" ? <span className="text-sea-700">{rupees(p.value)} left</span> : rupees(p.spent)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
