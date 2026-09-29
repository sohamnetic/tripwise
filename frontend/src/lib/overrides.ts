import type { Plan, TripOverrides, TripRequest } from "../api/types";

/** The request with a suggestion applied (picks accumulate). */
export function withUpgrade(req: TripRequest, o: TripOverrides): TripRequest {
  return {
    ...req,
    hotel_id: o.hotel_id ?? req.hotel_id ?? null,
    transport_ids: o.transport_ids.length ? o.transport_ids : req.transport_ids ?? [],
    must_include: [...new Set([...(req.must_include ?? []), ...o.must_include])],
    treat_dinners: o.treat_dinners || !!req.treat_dinners,
  };
}

/** The request without any picks: a fresh plan (used when editing or changing budget). */
export function withoutPicks(req: TripRequest): TripRequest {
  return { ...req, hotel_id: null, transport_ids: [], must_include: [], treat_dinners: false };
}

export interface Pick {
  key: string;
  label: string;
  remove: (req: TripRequest) => TripRequest;
}

/** The upgrades already applied to this plan, each removable. */
export function picksOf(plan: Plan): Pick[] {
  const req = plan.request;
  const picks: Pick[] = [];
  if (req.hotel_id && req.hotel_id === plan.hotel.id)
    picks.push({ key: "hotel", label: `🏨 ${plan.hotel.name}`, remove: (r) => ({ ...r, hotel_id: null }) });
  if (req.transport_ids?.length === 2)
    picks.push({
      key: "transport",
      label: `${plan.outbound.mode === "flight" ? "✈️" : plan.outbound.mode === "train" ? "🚆" : "🚌"} ${plan.outbound.carrier} · ${plan.outbound.service}`,
      remove: (r) => ({ ...r, transport_ids: [] }),
    });
  for (const id of req.must_include ?? []) {
    const place = plan.places.find((p) => p.id === id);
    if (place)
      picks.push({ key: id, label: `📍 ${place.name}`, remove: (r) => ({ ...r, must_include: (r.must_include ?? []).filter((x) => x !== id) }) });
  }
  if (req.treat_dinners)
    picks.push({ key: "dinners", label: "🍷 Nicer dinners", remove: (r) => ({ ...r, treat_dinners: false }) });
  return picks;
}
