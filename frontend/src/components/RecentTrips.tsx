import { useState } from "react";
import { Link } from "react-router-dom";
import { rupees } from "../lib/format";
import { forgetTrip, recentTrips } from "../lib/recent";
import { vibeFor } from "../lib/vibes";

const day = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short" });

/** Trips opened on this device, newest first. Nothing is shown until there's one. */
export default function RecentTrips() {
  const [trips, setTrips] = useState(recentTrips);
  if (!trips.length) return null;

  const remove = (id: string) => {
    forgetTrip(id);
    setTrips(recentTrips());
  };

  return (
    <section className="mx-auto mt-8 max-w-4xl px-4" aria-labelledby="recent-trips">
      <h2 id="recent-trips" className="text-sm font-bold uppercase tracking-wide text-muted">Your trips</h2>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        {trips.map((t) => (
          <li key={t.id} className="group relative">
            <Link to={`/trip/${t.id}`}
              className="flex items-center gap-3 rounded-2xl bg-white/85 p-3 pr-11 ring-1 ring-line backdrop-blur transition hover:ring-sea-500">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-paper text-2xl">{vibeFor(t.destination).emoji}</span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-bold">{t.origin} → {t.destination}</span>
                <span className="block text-xs text-muted">
                  {day(t.start)} – {day(t.end)} · {t.travellers} traveller{t.travellers > 1 ? "s" : ""} · {rupees(t.total)}
                </span>
              </span>
            </Link>
            <button onClick={() => remove(t.id)} aria-label={`Remove ${t.destination} trip from this list`}
              className="absolute right-2 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-full text-muted hover:bg-paper hover:text-ink">
              ×
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
