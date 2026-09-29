import type { Day, Place, SlotKind } from "../api/types";
import { dayColor, rupees, shortDate } from "../lib/format";

const ICON: Record<SlotKind, string> = {
  place: "📍",
  meal: "🍽️",
  travel: "🛺",
  checkin: "🏨",
  checkout: "🧳",
  arrival: "🛬",
  departure: "🛫",
};

export default function DayTimeline({ day, places }: { day: Day; places: Place[] }) {
  const byId = new Map(places.map((p) => [p.id, p]));
  let stop = 0;
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3" style={{ borderLeft: `4px solid ${dayColor(day.number)}` }}>
        <div>
          <div className="text-xs font-bold uppercase tracking-wide" style={{ color: dayColor(day.number) }}>
            Day {day.number} · {shortDate(day.date)}
          </div>
          <div className="font-bold">{day.title}</div>
        </div>
        <div className="text-right text-sm">
          <div className="font-extrabold">{rupees(day.cost)}</div>
          <div className="text-xs text-muted">food, fees & local travel</div>
        </div>
      </div>
      <ol className="px-4 py-2">
        {day.slots.map((s, i) => {
          const place = s.ref_id ? byId.get(s.ref_id) : undefined;
          if (s.kind === "place") stop += 1;
          if (s.kind === "travel") {
            return (
              <li key={i} className="flex items-center gap-3 py-1 pl-[3.25rem] text-xs text-muted">
                <span>{ICON.travel}</span>
                <span className="flex-1">{s.title} · {s.notes}</span>
                <span>{rupees(s.cost)}</span>
              </li>
            );
          }
          return (
            <li key={i} className="flex gap-3 border-b border-line/60 py-2.5 last:border-0">
              <span className="w-10 shrink-0 pt-0.5 text-xs font-semibold tabular-nums text-muted">{s.start}</span>
              <span className="relative shrink-0 pt-0.5">
                {s.kind === "place" ? (
                  <span className="grid h-6 w-6 place-items-center rounded-full text-[11px] font-bold text-white" style={{ background: dayColor(day.number) }}>
                    {stop}
                  </span>
                ) : (
                  <span className="grid h-6 w-6 place-items-center">{ICON[s.kind]}</span>
                )}
              </span>
              <div className="min-w-0 flex-1">
                <div className="font-semibold leading-snug">{s.title}</div>
                {s.notes && <div className="text-sm text-muted">{s.notes}</div>}
                {place && (
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                    <span>⭐ {place.rating}</span>
                    <span>🕒 {place.hours}</span>
                    {place.links.map((l) => (
                      <a key={l.label} href={l.url} target="_blank" rel="noreferrer" className="no-print rounded-full bg-sea-50 px-2.5 py-1.5 font-semibold text-sea-700 ring-1 ring-sea-100 hover:bg-sea-100 md:py-0.5">
                        {l.label === "Map" ? "Map ↗" : `Book on ${l.label} ↗`}
                      </a>
                    ))}
                  </div>
                )}
              </div>
              <span className="shrink-0 text-right text-sm font-semibold">
                {s.cost > 0 ? rupees(s.cost) : s.kind === "place" ? <span className="text-sea-700">Free</span> : ""}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
