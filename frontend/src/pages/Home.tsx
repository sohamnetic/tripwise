import { useRef, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useHealth } from "../api/client";
import type { Interest, Style, TransportPref, TripRequest } from "../api/types";
import CityInput from "../components/CityInput";
import RecentTrips from "../components/RecentTrips";
import Reveal from "../components/Reveal";
import Scene from "../components/Scene";
import Topo from "../components/Topo";
import { addDays, rupees, todayPlus } from "../lib/format";
import { EXPLORE, LOOKS, destinationsWith, vibeFor, type Tag } from "../lib/vibes";

const EXPLORE_PAGE = 8;
// Suggested in the city boxes before anything is typed.
const FROM_POPULAR = ["Kolkata", "Delhi", "Mumbai", "Bengaluru", "Chennai", "Hyderabad", "Pune", "Ahmedabad"];
const TO_POPULAR = ["Goa", "Manali", "Jaipur", "Udaipur", "Alleppey", "Leh", "Rishikesh", "Darjeeling"];

const LAST_KEY = "tripwise:last-request";

const STYLES: { value: Style; label: string; emoji: string; hint: string }[] = [
  { value: "budget", label: "Budget", emoji: "🎒", hint: "Hostels, trains, street food" },
  { value: "balanced", label: "Balanced", emoji: "🧳", hint: "Good value, a few treats" },
  { value: "comfort", label: "Comfort", emoji: "🛎️", hint: "Nicer stays, fewer hassles" },
  { value: "luxury", label: "Luxury", emoji: "🥂", hint: "5★ stays, fine dining" },
];

const INTERESTS: { value: Interest; label: string }[] = [
  { value: "beaches", label: "🏖️ Beaches" },
  { value: "history", label: "🏛️ History" },
  { value: "food", label: "🍛 Food" },
  { value: "nature", label: "🌿 Nature" },
  { value: "nightlife", label: "🌙 Nightlife" },
  { value: "shopping", label: "🛍️ Shopping" },
  { value: "adventure", label: "🪂 Adventure" },
];

const TRANSPORT: { value: TransportPref; label: string }[] = [
  { value: "any", label: "✨ Best option" },
  { value: "flight", label: "✈️ Flight" },
  { value: "train", label: "🚆 Train" },
  { value: "bus", label: "🚌 Bus" },
];

const BUDGET_CHIPS = [15000, 30000, 60000, 100000];


const STEPS = [
  { emoji: "📍", title: "Tell us the basics", text: "Where from, where to, dates, and one total budget." },
  { emoji: "🧮", title: "We fit it to your budget", text: "Transport, stay, food and sights, all priced in ₹ and added up in code." },
  { emoji: "🗺️", title: "Get a day-by-day plan", text: "Stops grouped by area, on a map, with times, costs and meals." },
  { emoji: "🔗", title: "Book it piece by piece", text: "One checklist with links to MakeMyTrip, Booking.com, IRCTC and more." },
];

const FACTS = [
  { emoji: "🗺️", value: String(Object.keys(LOOKS).length), label: "destinations in India & nearby" },
  { emoji: "₹", value: "100%", label: "priced in rupees" },
  { emoji: "🧮", value: "0", label: "prices made up by AI" },
  { emoji: "🔗", value: "10+", label: "sites to book on" },
];

function defaults(): TripRequest {
  const start = todayPlus(30);
  return {
    origin: "Kolkata",
    destination: "Goa",
    start_date: start,
    end_date: addDays(start, 4),
    travellers: 2,
    budget: 60000,
    style: "balanced",
    interests: ["beaches", "food"],
    transport: "any",
  };
}

function loadLast(): TripRequest | null {
  try {
    const raw = localStorage.getItem(LAST_KEY);
    return raw ? (JSON.parse(raw) as TripRequest) : null;
  } catch {
    return null;
  }
}

export default function Home() {
  const navigate = useNavigate();
  const location = useLocation();
  const navState = location.state as { request?: TripRequest; destination?: string } | null;
  const initial = navState?.request ?? loadLast() ?? defaults();
  const [form, setForm] = useState<TripRequest>(navState?.destination ? { ...initial, destination: navState.destination } : initial);
  const health = useHealth();
  const formRef = useRef<HTMLFormElement>(null);

  const set = <K extends keyof TripRequest>(key: K, value: TripRequest[K]) => setForm((f) => ({ ...f, [key]: value }));
  const nights = Math.round((Date.parse(form.end_date) - Date.parse(form.start_date)) / 86_400_000);
  const vibe = vibeFor(form.destination);
  const demo = health.data?.demo_mode;
  const demoCities = (health.data?.demo_destinations ?? []).map((c) => c.toLowerCase());
  const available = (city: string) => !demo || demoCities.includes(city.toLowerCase());

  const [tab, setTab] = useState<Tag>("beaches");
  const [showAll, setShowAll] = useState(false);
  const inTab = destinationsWith(tab);
  const shown = showAll ? inTab : inTab.slice(0, EXPLORE_PAGE);


  const submit = (e: FormEvent) => {
    e.preventDefault();
    try {
      localStorage.setItem(LAST_KEY, JSON.stringify(form));
    } catch {
      /* storage unavailable */
    }
    navigate("/planning", { state: { request: form } });
  };

  const toggleInterest = (i: Interest) =>
    set("interests", form.interests.includes(i) ? form.interests.filter((x) => x !== i) : [...form.interests, i]);

  const pickDestination = (city: string) => {
    set("destination", city);
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div>
      {/* hero: the scene follows whatever destination is typed */}
      <section className="relative h-[380px] overflow-hidden md:h-[440px]">
        <div key={vibe.tagline} className="absolute inset-0 fade-up">
          <Scene spec={vibe.spec} />
        </div>
        <div className="absolute inset-0 bg-gradient-to-b from-white/70 via-white/10 to-transparent" />
        <div className="relative mx-auto max-w-6xl px-4 pt-10 md:pt-14">
          <p className="inline-flex items-center gap-2 rounded-full bg-white/80 px-3 py-1 text-xs font-semibold text-sea-700 shadow-sm backdrop-blur">
            India-first · prices in ₹ · book anywhere
          </p>
          <h1 className="mt-4 max-w-2xl text-4xl font-extrabold leading-[1.05] tracking-tight text-ink md:text-6xl">
            Where to next?
          </h1>
          <div key={form.destination} className="fade-up mt-3 inline-flex max-w-full items-center gap-3 rounded-2xl bg-white/85 px-4 py-2.5 shadow-sm backdrop-blur">
            <span className="text-3xl">{vibe.emoji}</span>
            <div className="min-w-0">
              <div className="truncate text-lg font-extrabold">
                {form.origin || "Your city"} <span className="text-muted">→</span> {form.destination || "anywhere"}
              </div>
              <div className="truncate text-sm text-muted">{vibe.tagline}</div>
            </div>
          </div>
        </div>
      </section>

      <div className="relative mx-auto -mt-20 max-w-4xl px-4 md:-mt-28">
        <form ref={formRef} onSubmit={submit} className="card fade-up scroll-mt-20 space-y-5 p-5 shadow-xl shadow-slate-900/5 md:p-7">
          {demo && (
            <div className="rounded-xl bg-sand-100 px-3.5 py-2.5 text-sm text-sand-600">
              <b>Demo mode</b>: sample prices for {health.data?.demo_destinations.join(", ")}. Any origin city works.
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <CityInput label="From" value={form.origin} onChange={(v) => set("origin", v)} placeholder="Your city"
              popular={FROM_POPULAR} popularLabel="Big cities" />
            <CityInput label="To" value={form.destination} onChange={(v) => set("destination", v)} placeholder="Where to?"
              popular={TO_POPULAR} popularLabel="Popular trips" showTagline />
          </div>

          <div className="grid gap-4 sm:grid-cols-[1fr_1fr_auto]">
            <div>
              <label className="label" htmlFor="start">Leave on</label>
              <input id="start" type="date" className="input" value={form.start_date} min={todayPlus(1)}
                onChange={(e) => {
                  const start = e.target.value;
                  setForm((f) => ({ ...f, start_date: start, end_date: f.end_date <= start ? addDays(start, 3) : f.end_date }));
                }} required />
            </div>
            <div>
              <label className="label" htmlFor="end">Come back</label>
              <input id="end" type="date" className="input" value={form.end_date} min={addDays(form.start_date, 1)}
                max={addDays(form.start_date, 14)} onChange={(e) => set("end_date", e.target.value)} required />
            </div>
            <div>
              <span className="label">Travellers</span>
              <div className="flex h-[46px] items-center rounded-xl border border-line bg-white">
                <button type="button" className="h-full w-10 text-lg text-muted hover:text-ink" aria-label="Fewer travellers"
                  onClick={() => set("travellers", Math.max(1, form.travellers - 1))}>−</button>
                <span key={form.travellers} className="anim-pop w-8 text-center font-semibold">{form.travellers}</span>
                <button type="button" className="h-full w-10 text-lg text-muted hover:text-ink" aria-label="More travellers"
                  onClick={() => set("travellers", Math.min(10, form.travellers + 1))}>+</button>
              </div>
            </div>
          </div>
          <p className="-mt-2 text-xs text-muted">{nights > 0 ? `🌙 ${nights} night${nights > 1 ? "s" : ""}, ${nights + 1} days` : "Pick a return date after the start date"}</p>

          <div>
            <label className="label" htmlFor="budget">Total budget for everyone</label>
            <div className="relative">
              <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 font-semibold text-muted">₹</span>
              <input id="budget" className="input pl-8 text-lg font-bold" inputMode="numeric"
                value={form.budget ? form.budget.toLocaleString("en-IN") : ""}
                onChange={(e) => set("budget", Number(e.target.value.replace(/\D/g, "")) || 0)} required />
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {BUDGET_CHIPS.map((b) => (
                <button key={b} type="button" onClick={() => set("budget", b)}
                  className={`chip ${form.budget === b ? "border-sea-500 bg-sea-50 text-sea-700" : "border-line text-muted hover:border-sea-500"}`}>
                  {rupees(b)}
                </button>
              ))}
              {form.travellers > 1 && form.budget > 0 && (
                <span className="self-center text-xs text-muted">≈ {rupees(form.budget / form.travellers)} per person</span>
              )}
            </div>
          </div>

          <div>
            <span className="label">Travel style</span>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {STYLES.map((s) => (
                <button key={s.value} type="button" onClick={() => set("style", s.value)}
                  className={`rounded-xl border p-2.5 text-left transition ${form.style === s.value ? "border-sea-500 bg-sea-50 ring-4 ring-sea-100" : "border-line hover:border-sea-500"}`}>
                  <div className="text-sm font-bold"><span className={form.style === s.value ? "anim-pop inline-block" : "inline-block"}>{s.emoji}</span> {s.label}</div>
                  <div className="text-[11px] leading-tight text-muted">{s.hint}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-5 md:grid-cols-[1.4fr_1fr]">
            <div>
              <span className="label">Interests</span>
              <div className="flex flex-wrap gap-2">
                {INTERESTS.map((i) => {
                  const on = form.interests.includes(i.value);
                  return (
                    <button key={i.value} type="button" onClick={() => toggleInterest(i.value)}
                      className={`chip ${on ? "anim-pop border-sea-500 bg-sea-600 text-white" : "border-line bg-white text-ink hover:border-sea-500"}`}>
                      {i.label}
                    </button>
                  );
                })}
              </div>
            </div>
            <div>
              <span className="label">Getting there</span>
              <div className="flex flex-wrap gap-2">
                {TRANSPORT.map((t) => (
                  <button key={t.value} type="button" onClick={() => set("transport", t.value)}
                    className={`chip ${form.transport === t.value ? "border-sea-500 bg-sea-50 text-sea-700" : "border-line text-muted hover:border-sea-500"}`}>
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          </div>


          <button type="submit" className="btn-primary group w-full py-3.5 text-base shadow-lg shadow-sea-600/20" disabled={nights < 1}>
            <>Plan my trip to {form.destination || "…"} <span className="transition-transform group-hover:translate-x-1">→</span></>
          </button>
        </form>
      </div>

      <RecentTrips />

      {/* at a glance */}
      <div className="mx-auto mt-8 max-w-4xl px-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {FACTS.map((f, i) => (
            <Reveal key={f.label} delay={i * 60}>
              <div className="flex items-center gap-3 rounded-2xl bg-white/70 px-4 py-3 ring-1 ring-line backdrop-blur">
                <span className="text-2xl">{f.emoji}</span>
                <div>
                  <div className="text-lg font-extrabold leading-none">{f.value}</div>
                  <div className="mt-1 text-xs text-muted">{f.label}</div>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>

      {/* how it works: steps joined by a dotted flight path */}
      <section className="relative mt-16 overflow-hidden py-14">
        <div className="absolute inset-0 bg-white/60" />
        <Topo className="absolute -right-24 -top-10 w-[520px] opacity-80" />
        <Topo className="absolute -bottom-40 -left-32 w-[460px] rotate-180 opacity-60" color="#c7801a" />
        <div className="relative mx-auto max-w-6xl px-4">
          <Reveal>
            <p className="text-center text-xs font-bold uppercase tracking-[0.2em] text-sea-700">How it works</p>
            <h2 className="mt-2 text-center text-2xl font-extrabold tracking-tight md:text-4xl">From one budget to a full trip</h2>
          </Reveal>
          <div className="relative mt-10">
            {/* the route runs through the centre of each step's icon (desktop only) */}
            <svg viewBox="0 0 1000 80" preserveAspectRatio="none" className="absolute inset-x-[12%] top-0 hidden h-20 lg:block" aria-hidden="true">
              <path d="M0 40 C 110 0, 220 80, 333 40 S 555 0, 666 40 S 890 80, 1000 40" fill="none" stroke="#14a38b" strokeWidth="2.5" strokeDasharray="2 9" strokeLinecap="round" opacity="0.7" />
            </svg>
            <div className="relative grid gap-8 sm:grid-cols-2 lg:grid-cols-4 lg:gap-5">
              {STEPS.map((s, i) => (
                <Reveal key={s.title} delay={i * 100}>
                  <div className="group px-2 text-center">
                    <span className="relative mx-auto grid h-20 w-20 place-items-center rounded-full bg-white text-4xl shadow-lg shadow-sea-900/10 ring-8 ring-sea-50 transition group-hover:-translate-y-1 group-hover:ring-sea-100">
                      {s.emoji}
                      <span className="absolute -right-1 -top-1 grid h-7 w-7 place-items-center rounded-full bg-sea-600 text-xs font-bold text-white ring-4 ring-white">{i + 1}</span>
                    </span>
                    <div className="mt-4 font-bold">{s.title}</div>
                    <p className="mx-auto mt-1 max-w-[240px] text-sm leading-relaxed text-muted">{s.text}</p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* destination ideas, on a warm band */}
      <section className="relative overflow-hidden bg-gradient-to-b from-sand-100/70 to-transparent py-14">
        <div className="blob right-[-80px] top-[-60px] h-[300px] w-[300px] bg-coral-500/25" />
        <div className="blob left-[10%] bottom-[-120px] h-[280px] w-[280px] bg-sand-400/40" />
        <div className="relative mx-auto max-w-6xl px-4">
        <Reveal>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-sand-600">Where to?</p>
          <h2 className="mt-2 text-2xl font-extrabold tracking-tight md:text-4xl">Explore by vibe</h2>
          <p className="mt-1 text-muted">{Object.keys(LOOKS).length} destinations. Pick one and we'll plan the rest.</p>
        </Reveal>
        <div className="-mx-4 mt-5 flex gap-2 overflow-x-auto px-4 pb-1">
          {EXPLORE.map((e) => (
            <button key={e.tag} type="button" onClick={() => { setTab(e.tag); setShowAll(false); }}
              className={`chip shrink-0 ${tab === e.tag ? "border-ink bg-ink text-white" : "border-line bg-white/80 text-ink hover:border-sea-500"}`}>
              {e.label}
            </button>
          ))}
        </div>
        <div className="mt-5 grid grid-cols-2 gap-4 md:grid-cols-4">
          {shown.map((city) => {
            const v = vibeFor(city);
            const ok = available(city);
            return (
              <button key={`${tab}-${city}`} type="button" onClick={() => pickDestination(city)}
                className="card lift group fade-up block w-full overflow-hidden text-left">
                <div className="relative h-28 overflow-hidden md:h-32">
                  <Scene spec={v.spec} still className="transition-transform duration-700 group-hover:scale-105" />
                  {!ok && (
                    <span className="absolute right-2 top-2 rounded-full bg-white/90 px-2 py-0.5 text-[10px] font-semibold text-muted">
                      Needs live prices
                    </span>
                  )}
                </div>
                <div className="p-3">
                  <div className="truncate font-bold">{v.emoji} {city}</div>
                  <div className="truncate text-xs text-muted">{v.tagline}</div>
                </div>
              </button>
            );
          })}
        </div>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
          {inTab.length > EXPLORE_PAGE && (
            <button type="button" onClick={() => setShowAll((s) => !s)} className="btn-ghost">
              {showAll ? "Show fewer" : `Show all ${inTab.length}`}
            </button>
          )}
          <Link to="/destinations" className="text-sm font-semibold text-sea-700 hover:underline">See every destination →</Link>
        </div>
        </div>
      </section>

      {/* closing call to action over the destination's scene */}
      <section className="mx-auto mt-6 max-w-6xl px-4">
        <Reveal>
          <div className="relative overflow-hidden rounded-3xl shadow-xl shadow-slate-900/10">
            <div key={vibe.tagline} className="absolute inset-0 fade-up"><Scene spec={vibe.spec} /></div>
            <div className="absolute inset-0 bg-gradient-to-r from-sea-900/85 via-sea-900/55 to-transparent" />
            <div className="relative px-6 py-12 text-white md:px-12 md:py-16">
              <h2 className="max-w-md text-2xl font-extrabold leading-tight md:text-4xl">
                Your {form.destination || "next"} trip is one budget away.
              </h2>
              <p className="mt-2 max-w-md text-white/80">Transport, stay, food and every stop, fitted to {form.budget ? rupees(form.budget) : "your budget"}.</p>
              <button type="button" onClick={() => formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })}
                className="btn mt-6 bg-white text-sea-900 shadow-lg hover:bg-sea-50">
                Plan it now ↑
              </button>
            </div>
          </div>
        </Reveal>
      </section>
    </div>
  );
}
