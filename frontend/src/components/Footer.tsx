import { Link } from "react-router-dom";
import { InstallLink } from "./InstallApp";

const DESTINATIONS = ["Goa", "Manali", "Jaipur", "Varanasi", "Alleppey", "Leh"];
const PARTNERS = ["MakeMyTrip", "Booking.com", "IRCTC", "redBus", "Skyscanner", "Klook"];

export default function Footer() {
  return (
    <footer className="no-print relative mt-20 text-white/80">
      {/* wavy top edge */}
      <svg viewBox="0 0 1440 60" preserveAspectRatio="none" className="block h-10 w-full md:h-14" aria-hidden="true">
        <path d="M0 40 C 240 0, 480 0, 720 30 S 1200 60, 1440 20 V60 H0z" fill="#0b3b35" />
      </svg>
      <div className="relative overflow-hidden bg-sea-900">
        <div className="bg-dots-light absolute inset-0 opacity-60" />
        <div className="relative mx-auto grid max-w-6xl gap-10 px-4 py-12 md:grid-cols-[1.4fr_1fr_1fr]">
          <div>
            <div className="flex items-center gap-2 text-lg font-extrabold text-white">
              <img src="/logo.svg" alt="" className="h-8 w-8 rounded-lg ring-1 ring-white/20" />
              Tripwise
            </div>
            <p className="mt-3 max-w-sm text-sm leading-relaxed text-white/70">
              One budget in, a whole trip out: transport, stays, a day-by-day plan and links to book it all. Built for Indian travellers, priced in ₹.
            </p>
            <InstallLink className="mt-4 rounded-full bg-white/10 px-3.5 py-2 text-sm font-semibold text-white ring-1 ring-white/20 hover:bg-white/20" />
          </div>
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-sea-100">Popular trips</div>
            <ul className="mt-3 grid grid-cols-2 gap-y-2 text-sm">
              {DESTINATIONS.map((d) => (
                <li key={d}>
                  <Link to="/" state={{ destination: d }} className="hover:text-white">{d}</Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-sea-100">Book with</div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {PARTNERS.map((p) => (
                <span key={p} className="rounded-full bg-white/10 px-2.5 py-1 text-xs text-white/85">{p}</span>
              ))}
            </div>
          </div>
        </div>
        <div className="relative border-t border-white/10">
          <p className="mx-auto max-w-6xl px-4 py-5 text-xs text-white/55">
            Prices come from third-party sites and can change. Always confirm on the booking site before paying.
          </p>
        </div>
      </div>
    </footer>
  );
}
