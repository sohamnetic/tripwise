import type { Plan, TripRequest, Upgrade } from "../api/types";
import { rupees } from "../lib/format";
import { picksOf, withUpgrade } from "../lib/overrides";

const KIND_ICON: Record<Upgrade["kind"], string> = { activity: "🎟️", dining: "🍷", hotel: "🏨", transport: "🚀" };
const KIND_LABEL: Record<Upgrade["kind"], string> = { activity: "Do more", dining: "Eat better", hotel: "Stay better", transport: "Travel better" };

interface Props {
  plan: Plan;
  busy: boolean;
  onReplan: (req: TripRequest) => void;
}

// Shows what's left of the budget, the traveller's picks, and ways to spend the rest.
// Every price here is what applying it really adds: the backend re-plans with it to find out.
export default function SavingsCard({ plan, busy, onReplan }: Props) {
  const { summary: s, request: req } = plan;
  const picks = picksOf(plan);
  if (s.remaining <= 0 && !picks.length) return null;
  const pct = Math.round((s.remaining / s.budget) * 100);

  return (
    <div className="card overflow-hidden">
      <div className="flex flex-wrap items-center gap-4 bg-gradient-to-r from-sea-50 to-sand-100/60 p-5">
        <div className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-white text-3xl shadow-sm">🐷</div>
        <div className="min-w-0 flex-1">
          <div className="text-lg font-extrabold">
            {s.remaining > 0 ? <>You're saving {rupees(s.remaining)}</> : <>You're using your whole budget</>}
          </div>
          <p className="text-sm text-muted">
            {s.remaining > 0
              ? `That's ${pct}% of your budget, kept aside for shopping and surprises. Happy with that? Do nothing. Or spend a little on one of these:`
              : "Remove a pick below to free up money."}
          </p>
        </div>
      </div>

      {picks.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 border-t border-line px-5 py-3 text-sm">
          <span className="font-semibold text-muted">Your picks:</span>
          {picks.map((p) => (
            <span key={p.key} className="inline-flex items-center gap-1 rounded-full bg-sea-50 py-1 pl-3 pr-1 text-sea-700 ring-1 ring-sea-100">
              {p.label}
              <button className="grid h-5 w-5 place-items-center rounded-full hover:bg-sea-100" title="Remove" aria-label={`Remove ${p.label}`}
                disabled={busy} onClick={() => onReplan(p.remove(req))}>×</button>
            </span>
          ))}
        </div>
      )}

      {plan.upgrades.length > 0 && (
        <ul className="divide-y divide-line border-t border-line">
          {plan.upgrades.map((u) => {
            const after = s.remaining - u.extra_cost;
            return (
              <li key={u.id} className="flex flex-wrap items-center gap-3 px-5 py-3.5 transition hover:bg-paper sm:flex-nowrap">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-paper text-xl">{KIND_ICON[u.kind]}</span>
                <div className="min-w-0 flex-1">
                  <div className="text-[11px] font-bold uppercase tracking-wide text-muted">{KIND_LABEL[u.kind]}</div>
                  <div className="font-semibold leading-snug">{u.title}</div>
                  <div className="text-sm text-muted">{u.detail}</div>
                </div>
                <div className="flex items-center gap-3 sm:flex-col sm:items-end sm:gap-1">
                  <div className="text-right">
                    <div className="font-extrabold text-ink">+{rupees(u.extra_cost)}</div>
                    <div className="text-[11px] text-muted">{rupees(after)} still saved</div>
                  </div>
                  <button className="btn-primary px-3 py-1.5 text-xs" disabled={busy} onClick={() => onReplan(withUpgrade(req, u.apply))}>
                    Add to my trip
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
