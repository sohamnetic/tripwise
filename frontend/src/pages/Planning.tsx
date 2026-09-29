import { useEffect } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useJob } from "../api/client";
import type { TripRequest } from "../api/types";
import Scene from "../components/Scene";
import { useRotate } from "../lib/hooks";
import { TRAVEL_TIPS, vibeFor } from "../lib/vibes";

const STEPS = [
  { at: 10, label: "Understanding your trip" },
  { at: 30, label: "Finding flights, trains, hotels & places" },
  { at: 60, label: "Fitting everything into your budget" },
  { at: 80, label: "Building your day-by-day plan" },
  { at: 95, label: "Adding booking links" },
];

// A plane flying along a dotted arc from origin to destination.
function Flight({ from, to }: { from: string; to: string }) {
  const path = "M40 110 C 160 10, 360 10, 480 110";
  return (
    <div className="relative">
      <svg viewBox="0 0 520 140" className="w-full" aria-hidden="true">
        <path d={path} fill="none" stroke="#cbd5e1" strokeWidth="2.5" strokeDasharray="2 9" strokeLinecap="round" />
        <circle cx="40" cy="110" r="7" fill="#0f172a" />
        <circle cx="480" cy="110" r="9" fill="#14a38b" className="anim-glow" />
        <circle cx="480" cy="110" r="4" fill="#fff" />
        <g>
          {/* the emoji points north-east; turn it to face along the path */}
          <text fontSize="26" textAnchor="middle" dominantBaseline="central" transform="rotate(45)">✈️</text>
          <animateMotion dur="3.2s" repeatCount="indefinite" rotate="auto" path={path} keyPoints="0;1" keyTimes="0;1" calcMode="spline" keySplines="0.45 0 0.55 1" />
        </g>
      </svg>
      <div className="-mt-3 flex justify-between px-1 text-sm font-bold">
        <span>{from}</span>
        <span className="text-sea-700">{to}</span>
      </div>
    </div>
  );
}

export default function Planning() {
  const { jobId = "" } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const request = (location.state as { request?: TripRequest } | null)?.request;
  const { data, error } = useJob(jobId);
  const tip = useRotate(TRAVEL_TIPS.length, 3500);
  const vibe = vibeFor(request?.destination);

  useEffect(() => {
    if (data?.status === "done" && data.trip_id) navigate(`/trip/${data.trip_id}`, { replace: true });
  }, [data, navigate]);

  const failed = data?.status === "error" || error;
  const progress = data?.progress ?? 0;

  return (
    <div className="relative min-h-[calc(100vh-56px)] overflow-hidden">
      <div className="absolute inset-0 opacity-60">
        <Scene spec={vibe.spec} />
      </div>
      <div className="absolute inset-0 bg-white/40 backdrop-blur-[2px]" />
      <div className="relative mx-auto max-w-lg px-4 py-12 md:py-16">
        <div className="card fade-up p-6 shadow-xl shadow-slate-900/10 md:p-8">
          {failed ? (
            <>
              <div className="mb-3 text-4xl">😕</div>
              <h1 className="text-xl font-bold">We couldn't plan this trip</h1>
              <p className="mt-2 text-muted">{data?.error ?? (error as Error)?.message}</p>
              <Link to="/" state={location.state} className="btn-primary mt-6">← Change the trip</Link>
            </>
          ) : (
            <>
              <h1 className="text-xl font-bold">
                Planning your {request ? `${request.destination} ` : ""}trip {vibe.emoji}
              </h1>
              <p className="mt-1 text-sm text-muted">This usually takes under a minute.</p>
              {request && (
                <div className="mt-4">
                  <Flight from={request.origin} to={request.destination} />
                </div>
              )}
              <div className="mt-5 h-2 overflow-hidden rounded-full bg-sea-50">
                <div className="h-full rounded-full bg-gradient-to-r from-sea-500 to-sand-400 transition-all duration-700" style={{ width: `${Math.max(progress, 4)}%` }} />
              </div>
              <ol className="mt-5 space-y-3">
                {STEPS.map((s, i) => {
                  const done = progress > s.at;
                  const active = progress === s.at;
                  return (
                    <li key={s.label} className="flex items-center gap-3 text-sm">
                      <span className={`grid h-6 w-6 place-items-center rounded-full text-xs font-bold transition ${done ? "anim-pop bg-sea-600 text-white" : active ? "bg-sea-100 text-sea-700 ring-2 ring-sea-500" : "bg-paper text-muted ring-1 ring-line"}`}>
                        {done ? "✓" : i + 1}
                      </span>
                      <span className={done ? "text-ink" : active ? "font-semibold text-ink" : "text-muted"}>{s.label}</span>
                      {active && <span className="ml-auto h-4 w-4 animate-spin rounded-full border-2 border-sea-500 border-t-transparent" />}
                    </li>
                  );
                })}
              </ol>
              <div className="mt-6 rounded-xl bg-sand-100/70 px-4 py-3 text-sm">
                <div className="text-[11px] font-bold uppercase tracking-wide text-sand-600">Travel tip</div>
                <p key={tip} className="fade-up mt-0.5 text-ink/80">{TRAVEL_TIPS[tip]}</p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
