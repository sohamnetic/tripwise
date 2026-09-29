import type { TransportOption } from "../api/types";
import { MODE_ICON, duration, rupees, shortDate, time } from "../lib/format";
import PriceBadge from "./PriceBadge";

export default function TransportCard({ opt, label, demo }: { opt: TransportOption; label: string; demo: boolean }) {
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</div>
          <div className="mt-1 font-bold">
            {MODE_ICON[opt.mode]} {opt.carrier} <span className="font-medium text-muted">· {opt.service}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-extrabold">{rupees(opt.total_price)}</div>
          <div className="flex items-center justify-end gap-1.5 text-xs text-muted">
            {rupees(opt.price_per_person)}/person <PriceBadge estimate={opt.is_estimate} demo={demo && opt.mode === "flight"} />
          </div>
        </div>
      </div>
      <div className="mt-3 flex items-center gap-3 text-sm">
        <div>
          <div className="font-bold">{time(opt.depart)}</div>
          <div className="text-xs text-muted">{opt.from_city} · {shortDate(opt.depart)}</div>
        </div>
        <div className="flex flex-1 items-center gap-2 text-xs text-muted">
          <span className="h-px flex-1 bg-line" />
          {duration(opt.duration_min)}
          <span className="h-px flex-1 bg-line" />
        </div>
        <div className="text-right">
          <div className="font-bold">{time(opt.arrive)}</div>
          <div className="text-xs text-muted">{opt.to_city} · {shortDate(opt.arrive)}</div>
        </div>
      </div>
      <div className="no-print mt-3 flex flex-wrap gap-2">
        {opt.links.map((l) => (
          <a key={l.label} href={l.url} target="_blank" rel="noreferrer" className="chip border-line text-sea-700 hover:border-sea-500">
            Book on {l.label} ↗
          </a>
        ))}
      </div>
    </div>
  );
}
