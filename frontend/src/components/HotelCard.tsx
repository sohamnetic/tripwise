import type { Hotel } from "../api/types";
import { rupees } from "../lib/format";
import PriceBadge from "./PriceBadge";

export default function HotelCard({ hotel, nights, pick, demo }: { hotel: Hotel; nights: number; pick?: boolean; demo: boolean }) {
  return (
    <div className={`card p-4 ${pick ? "ring-2 ring-sea-500" : ""}`}>
      {pick && <div className="mb-2 text-xs font-bold uppercase tracking-wide text-sea-700">Our pick</div>}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-bold leading-snug">{hotel.name}</div>
          <div className="text-sm text-muted">
            {hotel.area}{hotel.stars > 0 && <> · {"★".repeat(hotel.stars)}</>}
          </div>
          <div className="mt-1 text-sm">
            <span className="rounded-md bg-sea-600 px-1.5 py-0.5 text-xs font-bold text-white">{hotel.rating.toFixed(1)}</span>{" "}
            <span className="text-muted">{hotel.reviews.toLocaleString("en-IN")} reviews</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-extrabold">{rupees(hotel.total_price)}</div>
          <div className="flex items-center justify-end gap-1.5 text-xs text-muted">
            {rupees(hotel.nightly_price)}/night × {nights} × {hotel.rooms} room{hotel.rooms > 1 ? "s" : ""}
          </div>
          <div className="mt-1"><PriceBadge estimate={false} demo={demo} /></div>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {hotel.amenities.map((a) => (
          <span key={a} className="rounded-md bg-paper px-2 py-0.5 text-xs text-muted">{a}</span>
        ))}
      </div>
      <div className="no-print mt-3 flex flex-wrap gap-2">
        {hotel.links.map((l) => (
          <a key={l.label} href={l.url} target="_blank" rel="noreferrer" className="chip border-line text-sea-700 hover:border-sea-500">
            {l.label} ↗
          </a>
        ))}
      </div>
    </div>
  );
}
