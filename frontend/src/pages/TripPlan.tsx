import { useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTrip } from "../api/client";
import type { Style, TripRequest } from "../api/types";
import BookingChecklist from "../components/BookingChecklist";
import BudgetBreakdown from "../components/BudgetBreakdown";
import DayTimeline from "../components/DayTimeline";
import HotelCard from "../components/HotelCard";
import PackingList from "../components/PackingList";
import SavingsCard from "../components/SavingsCard";
import Reveal from "../components/Reveal";
import Scene from "../components/Scene";
import Topo from "../components/Topo";
import TransportCard from "../components/TransportCard";
import TripMap from "../components/TripMap";
import WeatherCard from "../components/WeatherCard";
import { MODE_ICON, dayColor, duration, rupees, shortDate } from "../lib/format";
import { useCountUp } from "../lib/hooks";
import { withoutPicks } from "../lib/overrides";
import { vibeFor } from "../lib/vibes";

const STYLE_ORDER: Style[] = ["budget", "balanced", "comfort"];

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <Reveal className="mt-12">
      <section>
        <div className="mb-2 h-1 w-10 rounded-full bg-gradient-to-r from-sea-500 to-sand-400" />
        <h2 className="text-xl font-extrabold tracking-tight md:text-2xl">{title}</h2>
        {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
        <div className="mt-4">{children}</div>
      </section>
    </Reveal>
  );
}

function Stat({ label, value, tone = "text-ink", children }: { label: string; value: number; tone?: string; children?: ReactNode }) {
  const shown = useCountUp(value);
  return (
    <div className="card p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-1 text-2xl font-extrabold tabular-nums md:text-3xl ${tone}`}>{rupees(shown)}</div>
      {children}
    </div>
  );
}

function Loading() {
  return (
    <div>
      <div className="h-[260px] skeleton" />
      <div className="mx-auto -mt-12 grid max-w-6xl gap-3 px-4 sm:grid-cols-3">
        {[0, 1, 2].map((i) => <div key={i} className="card h-24 skeleton" />)}
      </div>
    </div>
  );
}

export default function TripPlan() {
  const { tripId = "" } = useParams();
  const navigate = useNavigate();
  const { data: plan, isLoading, error } = useTrip(tripId);
  const [activeDay, setActiveDay] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const replan = (request: TripRequest) => navigate("/planning", { state: { request } });

  if (isLoading) return <Loading />;
  if (error || !plan)
    return (
      <div className="mx-auto max-w-md px-4 py-20 text-center">
        <div className="text-4xl">🧭</div>
        <p className="mt-2 text-muted">{(error as Error)?.message ?? "Trip not found."}</p>
        <Link to="/" className="btn-primary mt-4">Plan a trip</Link>
      </div>
    );

  const { request: req, summary: s } = plan;
  const demo = plan.data_mode === "demo";
  const vibe = vibeFor(plan.destination.name);
  const days = activeDay ? plan.days.filter((d) => d.number === activeDay) : plan.days;
  const styleIdx = STYLE_ORDER.indexOf(req.style);

  const share = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      window.prompt("Copy this link", window.location.href);
    }
  };

  const variant = (factor: number, styleStep: number): TripRequest => ({
    ...withoutPicks(req),
    budget: Math.round((req.budget * factor) / 1000) * 1000,
    style: STYLE_ORDER[Math.min(2, Math.max(0, styleIdx + styleStep))],
  });
  const cheaper = variant(0.75, -1);
  const fancier = variant(1.4, +1);

  return (
    <div className="relative pb-16">
      {/* soft destination-coloured wash behind the page, with contour lines */}
      <div className="pointer-events-none absolute inset-x-0 top-[240px] -z-10 h-[1400px]"
        style={{ background: `linear-gradient(to bottom, ${vibe.tint}, transparent)` }} />
      <Topo className="absolute right-[-160px] top-[700px] -z-10 w-[560px] opacity-70" color={vibe.accent} />
      <Topo className="absolute left-[-200px] top-[1700px] -z-10 w-[520px] rotate-90 opacity-50" color={vibe.accent} />
      {/* hero */}
      <section className="relative h-[340px] overflow-hidden sm:h-[280px] md:h-[300px]">
        <Scene spec={vibe.spec} />
        <div className="absolute inset-0 bg-gradient-to-b from-white/75 via-white/20 to-transparent" />
        <div className="relative mx-auto flex max-w-6xl flex-wrap items-start justify-between gap-4 px-4 pt-7">
          <div className="fade-up">
            <div className="flex flex-wrap gap-1.5 text-xs font-semibold">
              {[`${shortDate(req.start_date)} → ${shortDate(req.end_date)}`, `${s.nights} nights`,
                `${req.travellers} traveller${req.travellers > 1 ? "s" : ""}`, req.style].map((t) => (
                <span key={t} className="rounded-full bg-white/85 px-2.5 py-1 capitalize text-ink/80 shadow-sm backdrop-blur">{t}</span>
              ))}
            </div>
            <h1 className="mt-3 text-3xl font-extrabold tracking-tight md:text-5xl">
              {vibe.emoji} {plan.destination.name}
            </h1>
            <p className="mt-1 font-semibold text-ink/70">from {plan.origin.name} · {vibe.tagline}</p>
          </div>
          <div className="no-print flex gap-2">
            <Link to="/" state={{ request: withoutPicks(req) }} className="btn-ghost bg-white/90">✏️ Edit</Link>
            <button onClick={share} className="btn-ghost bg-white/90">{copied ? "✓ Copied" : "🔗 Share"}</button>
            <button onClick={() => window.print()} className="btn-ghost bg-white/90">🖨️ PDF</button>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-6xl px-4">
        {/* summary */}
        <div className="relative -mt-12 grid grid-cols-2 gap-3 sm:grid-cols-4 md:-mt-16">
          <div className="col-span-2">
            <Stat label="Estimated total" value={s.total_cost}>
              <div className="mt-1 text-sm text-muted">of your {rupees(s.budget)} budget</div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-paper">
                <div className={`h-full rounded-full transition-all duration-1000 ${s.within_budget ? "bg-gradient-to-r from-sea-500 to-sea-600" : "bg-coral-500"}`}
                  style={{ width: `${Math.min(100, (s.total_cost / s.budget) * 100)}%` }} />
              </div>
            </Stat>
          </div>
          <Stat label={s.within_budget ? "You're saving" : "Over budget"} value={Math.abs(s.remaining)} tone={s.within_budget ? "text-sea-700" : "text-coral-500"}>
            <div className="mt-1 text-sm text-muted">{s.within_budget ? "see ways to spend it below" : "try the cheaper version"}</div>
          </Stat>
          <Stat label="Per person" value={s.per_person}>
            <div className="mt-1 text-sm text-muted">everything included</div>
          </Stat>
        </div>
        <p className="mt-2 text-xs text-muted">
          {demo ? "Sample prices (demo mode)." : `Prices checked ${new Date(plan.prices_checked_at).toLocaleString("en-IN")}.`}{" "}
          Train, bus, food and local-travel costs are estimates.
        </p>

        {plan.warnings.length > 0 && (
          <div className="mt-4 space-y-1.5 rounded-2xl bg-sand-100 px-4 py-3 text-sm text-sand-600">
            {plan.warnings.map((w) => <p key={w}>⚠️ {w}</p>)}
          </div>
        )}

        <div className="no-print mt-5">
          <SavingsCard plan={plan} busy={false} onReplan={replan} />
        </div>

        {/* replan */}
        <div className="no-print mt-4 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-muted">Not quite right?</span>
          <button className="chip border-line bg-white hover:border-sea-500" onClick={() => replan(cheaper)}>
            💸 Cheaper version ({rupees(cheaper.budget)})
          </button>
          <button className="chip border-line bg-white hover:border-sea-500" onClick={() => replan(fancier)}>
            ✨ More comfort ({rupees(fancier.budget)})
          </button>
        </div>

        <Section title="💰 Where the money goes">
          <div className="card p-5">
            <BudgetBreakdown lines={plan.budget} budget={s.budget} />
          </div>
        </Section>

        <Section title={`${MODE_ICON[plan.outbound.mode]} Getting there`} subtitle={`Best ${plan.outbound.mode} for a ${req.style} trip`}>
          <div className="grid gap-3 md:grid-cols-2">
            <TransportCard opt={plan.outbound} label="Outbound" demo={demo} />
            <TransportCard opt={plan.inbound} label="Return" demo={demo} />
          </div>
          {plan.transport_alternatives.length > 0 && (
            <details className="mt-3">
              <summary className="cursor-pointer text-sm font-semibold text-sea-700">Other outbound options ({plan.transport_alternatives.length})</summary>
              <div className="card mt-2 divide-y divide-line">
                {plan.transport_alternatives.map((o) => (
                  <div key={o.id} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
                    <span>{MODE_ICON[o.mode]} {o.carrier} · {o.service}</span>
                    <span className="text-muted">{duration(o.duration_min)}</span>
                    <span className="font-semibold">{rupees(o.total_price)}</span>
                  </div>
                ))}
              </div>
            </details>
          )}
        </Section>

        <Section title="🏨 Where you'll stay" subtitle={`${s.nights} nights · ${s.rooms} room${s.rooms > 1 ? "s" : ""}`}>
          <div className="grid gap-3 md:grid-cols-3">
            <HotelCard hotel={plan.hotel} nights={s.nights} pick demo={demo} />
            {plan.hotel_alternatives.map((h) => <HotelCard key={h.id} hotel={h} nights={s.nights} demo={demo} />)}
          </div>
        </Section>

        <Section
          title="🗓️ Day by day"
          subtitle={`${plan.planned_by === "ai" ? "Places chosen by Claude" : "Places chosen by our built-in planner"}, grouped by area to cut travel time. Costs are calculated, not guessed.`}
        >
          <div className="no-print sticky top-14 z-[500] -mx-4 mb-4 flex gap-2 overflow-x-auto bg-paper/90 px-4 py-2 backdrop-blur">
            <button onClick={() => setActiveDay(null)} className={`chip shrink-0 ${activeDay === null ? "border-ink bg-ink text-white" : "border-line bg-white text-muted"}`}>All days</button>
            {plan.days.map((d) => (
              <button key={d.number} onClick={() => setActiveDay(d.number)}
                className={`chip shrink-0 ${activeDay === d.number ? "text-white" : "border-line bg-white text-muted"}`}
                style={activeDay === d.number ? { background: dayColor(d.number), borderColor: dayColor(d.number) } : undefined}>
                <span className="h-2 w-2 rounded-full" style={{ background: activeDay === d.number ? "#fff" : dayColor(d.number) }} />
                Day {d.number}
              </button>
            ))}
          </div>
          <div className="grid gap-5 lg:grid-cols-[1fr_420px]">
            <div className="space-y-4">
              {days.map((d) => <div key={d.number} className="fade-up"><DayTimeline day={d} places={plan.places} /></div>)}
            </div>
            <div className="no-print lg:sticky lg:top-28 lg:self-start">
              <div className="card overflow-hidden p-1.5">
                <TripMap days={plan.days} hotel={plan.hotel} activeDay={activeDay} />
              </div>
            </div>
          </div>
        </Section>

        <Section title="🧳 Before you go">
          <div className="space-y-3">
            <WeatherCard city={plan.destination} start={req.start_date} end={req.end_date} />
            <PackingList plan={plan} />
          </div>
        </Section>

        <Section title="✅ Book it" subtitle="Everything you need to book, in order. Tick items off as you go.">
          <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
            <BookingChecklist tripId={plan.id} items={plan.checklist} />
            <div>
              <div className="mb-2 text-sm font-bold">Prefer a ready-made package?</div>
              <div className="grid gap-2 sm:grid-cols-2">
                {plan.packages.map((p) => (
                  <a key={p.provider} href={p.url} target="_blank" rel="noreferrer" className="card lift block p-4 hover:border-sea-500">
                    <div className="text-xs font-semibold uppercase tracking-wide text-muted">{p.provider}</div>
                    <div className="mt-1 font-semibold">{p.title} ↗</div>
                  </a>
                ))}
              </div>
              <p className="mt-2 text-xs text-muted">Compare package prices against our total of {rupees(s.total_cost)}.</p>
            </div>
          </div>
        </Section>

        {plan.tips.length > 0 && (
          <Section title="💡 Good to know">
            <ul className="card space-y-2 p-5 text-sm">
              {plan.tips.map((t) => <li key={t}>{t}</li>)}
            </ul>
          </Section>
        )}
      </div>
    </div>
  );
}
