"""Budget engine: plain Python, no LLM. Every rupee shown to the user is computed here."""

import math
from dataclasses import dataclass, field

from ..models.schemas import BudgetLine, Day, Hotel, Place, TransportOption, TripRequest
from ..providers.geocode import haversine_km

SPLITS: dict[str, dict[str, float]] = {
    "budget":   {"stay": 0.40, "food": 0.25, "activities": 0.15, "local": 0.10, "buffer": 0.10},
    "balanced": {"stay": 0.45, "food": 0.20, "activities": 0.15, "local": 0.10, "buffer": 0.10},
    "comfort":  {"stay": 0.50, "food": 0.18, "activities": 0.15, "local": 0.10, "buffer": 0.07},
}
# How much one hour of travel time is "worth" per person when comparing transport options.
TIME_VALUE_PER_HOUR = {"budget": 60, "balanced": 250, "comfort": 600}
TRAIN_CLASS_DISCOMFORT = {
    "Sleeper (SL)": {"budget": 0, "balanced": 60, "comfort": 150},
    "AC 3-tier (3A)": {"budget": 0, "balanced": 0, "comfort": 40},
}
# Largest share of the budget that transport may take before we switch to the cheapest option.
MAX_TRANSPORT_SHARE = 0.55
# Hotel scoring: how much each style values stars vs. saving money (share of stay budget).
HOTEL_WEIGHTS = {
    "budget": {"stars": 0.1, "price": 3.0},
    "balanced": {"stars": 0.6, "price": 0.5},
    "comfort": {"stars": 1.2, "price": 0.0},
}
KM_PENALTY = 0.12  # score points per km of average distance to the top sights
MIN_FOOD_PER_PERSON_DAY = 500
MIN_LOCAL_PER_PERSON_DAY = 150

LABELS = {
    "transport": "Getting there & back",
    "stay": "Stay",
    "food": "Food",
    "activities": "Activities & entry fees",
    "local": "Local travel",
    "buffer": "Emergency buffer",
}


class BudgetTooLowError(ValueError):
    def __init__(self, minimum: int, detail: str):
        self.minimum = minimum
        super().__init__(f"{detail} You'd need at least ₹{minimum:,} for this trip.")


@dataclass
class BudgetDecision:
    outbound: TransportOption
    inbound: TransportOption
    alternatives: list[TransportOption]
    hotel: Hotel
    hotel_alternatives: list[Hotel]
    alloc: dict[str, int]
    warnings: list[str] = field(default_factory=list)


def _score(opt: TransportOption, style: str, pax: int) -> float:
    hours = opt.duration_min / 60
    # Discomfort of basic train classes on long journeys, per person-hour, by style:
    # a balanced traveller would rather pay for AC 3-tier than sit 40 hours in Sleeper.
    discomfort = TRAIN_CLASS_DISCOMFORT.get(opt.service, {}).get(style, 0)
    return opt.total_price + (TIME_VALUE_PER_HOUR[style] + discomfort) * hours * pax


def _pairs(outbound: list[TransportOption], inbound: list[TransportOption], modes: set[str]):
    for mode in modes:
        outs = [o for o in outbound if o.mode == mode]
        ins = [i for i in inbound if i.mode == mode]
        if outs and ins:
            yield outs, ins


def choose_transport(req: TripRequest, outbound: list[TransportOption], inbound: list[TransportOption]):
    """Returns (outbound, inbound, alternatives, warnings)."""
    warnings: list[str] = []
    style_key = lambda o: _score(o, req.style, req.travellers)

    # The traveller picked specific options (an accepted upgrade): use them as-is.
    if len(req.transport_ids) == 2:
        out = next((o for o in outbound if o.id == req.transport_ids[0]), None)
        back = next((i for i in inbound if i.id == req.transport_ids[1]), None)
        if out and back:
            return out, back, sorted((o for o in outbound if o.id != out.id), key=style_key)[:4], warnings
        warnings.append("The transport you picked is no longer available, so we chose the best current option.")

    modes = {o.mode for o in outbound} & {i.mode for i in inbound}
    if not modes:
        raise BudgetTooLowError(0, "We couldn't find any way to travel between these cities.")
    if req.transport != "any":
        if req.transport in modes:
            modes = {req.transport}
        else:
            warnings.append(f"No {req.transport} option on this route, so we picked the best alternative.")

    def best(opts, key):
        return min(opts, key=key)

    price_key = lambda o: o.total_price

    candidates = [(best(outs, style_key), best(ins, style_key)) for outs, ins in _pairs(outbound, inbound, modes)]
    out, back = min(candidates, key=lambda p: style_key(p[0]) + style_key(p[1]))

    cap = req.budget * MAX_TRANSPORT_SHARE
    if out.total_price + back.total_price > cap:
        # Best option (for this style) among those under the cap; failing that, the cheapest.
        pairs = [(o, i) for outs, ins in _pairs(outbound, inbound, modes) for o in outs for i in ins if o.mode == i.mode]
        under = [p for p in pairs if p[0].total_price + p[1].total_price <= cap]
        if under:
            c_out, c_back = min(under, key=lambda p: style_key(p[0]) + style_key(p[1]))
        else:
            c_out, c_back = min(pairs, key=lambda p: price_key(p[0]) + price_key(p[1]))
        warnings.append(f"Picked {c_out.carrier} ({c_out.service}) instead of {out.carrier} to leave room in your budget.")
        out, back = c_out, c_back

    alternatives = sorted((o for o in outbound if o.id != out.id), key=style_key)[:4]
    return out, back, alternatives, warnings


def _mean_km_to_sights(h: Hotel, places: list[Place]) -> float:
    top = sorted(places, key=lambda p: -p.rating)[:10]
    if not top:
        return 0.0
    return sum(haversine_km(h.lat, h.lng, p.lat, p.lng) for p in top) / len(top)


def choose_hotel(hotels: list[Hotel], stay_budget: int, style: str, places: list[Place] = ()) -> tuple[Hotel, list[Hotel], bool]:
    """Returns (pick, alternatives, fits_budget). Location counts: a hotel far from the
    sights costs more in daily travel than it saves."""
    affordable = [h for h in hotels if h.total_price <= stay_budget]
    if not affordable:
        pick = min(hotels, key=lambda h: h.total_price)
        return pick, sorted((h for h in hotels if h.id != pick.id), key=lambda h: h.total_price)[:2], False

    alloc = max(stay_budget, 1)
    weights = HOTEL_WEIGHTS[style]

    def score(h: Hotel) -> float:
        return (h.rating * 2 + h.stars * weights["stars"] - weights["price"] * h.total_price / alloc
                - KM_PENALTY * _mean_km_to_sights(h, list(places)))

    good = [h for h in affordable if h.rating >= 3.8] or affordable
    ranked = sorted(good, key=score, reverse=True)
    return ranked[0], ranked[1:3], True


def plan_budget(req: TripRequest, outbound, inbound, hotels: list[Hotel], places: list[Place] = ()) -> BudgetDecision:
    """Splits the budget based on the default picks, then applies any upgrades the traveller
    chose. Upgrades are paid from the savings (buffer) only, so they never shrink the money
    for food and activities."""
    base = plan_default_budget(req.model_copy(update={"transport_ids": [], "hotel_id": None}), outbound, inbound, hotels, places)
    alloc, warnings = dict(base.alloc), list(base.warnings)
    out, back, alternatives, hotel, hotel_alts = base.outbound, base.inbound, base.alternatives, base.hotel, base.hotel_alternatives

    if len(req.transport_ids) == 2:
        p_out, p_back, p_alts, p_warn = choose_transport(req, outbound, inbound)
        warnings += p_warn
        if (p_out.id, p_back.id) != (out.id, back.id):
            alloc["buffer"] -= (p_out.total_price + p_back.total_price) - (out.total_price + back.total_price)
            alloc["transport"] = p_out.total_price + p_back.total_price
            out, back, alternatives = p_out, p_back, p_alts

    if req.hotel_id:
        picked = next((h for h in hotels if h.id == req.hotel_id), None)
        if not picked:
            warnings.append("The hotel you picked is no longer available, so we kept our pick.")
        elif picked.id != hotel.id:
            alloc["buffer"] -= picked.total_price - hotel.total_price
            alloc["stay"] = picked.total_price
            hotel_alts = [h for h in [hotel, *hotel_alts] if h.id != picked.id][:2]
            hotel = picked

    return BudgetDecision(out, back, alternatives, hotel, hotel_alts, alloc, warnings)


def plan_default_budget(req: TripRequest, outbound, inbound, hotels: list[Hotel], places: list[Place] = ()) -> BudgetDecision:
    out, back, alternatives, warnings = choose_transport(req, outbound, inbound)
    transport = out.total_price + back.total_price
    days = req.nights + 1

    cheapest_stay = min(h.total_price for h in hotels)
    minimum = transport + cheapest_stay + (MIN_FOOD_PER_PERSON_DAY + MIN_LOCAL_PER_PERSON_DAY) * req.travellers * days
    if minimum > req.budget:
        raise BudgetTooLowError(int(math.ceil(minimum / 500) * 500), "This budget is too tight for the trip.")

    remaining = req.budget - transport
    alloc = {k: int(remaining * share) for k, share in SPLITS[req.style].items()}
    alloc["transport"] = transport

    hotel, hotel_alts, fits = choose_hotel(hotels, alloc["stay"], req.style, places)
    diff = alloc["stay"] - hotel.total_price
    if not fits:
        warnings.append("Even the cheapest stay is above the planned stay budget; we trimmed other categories to fit.")
        deficit = -diff
        for key in ("buffer", "activities", "local", "food"):
            take = min(deficit, alloc[key] - (0 if key == "buffer" else alloc[key] // 2))
            alloc[key] -= take
            deficit -= take
    else:
        alloc["buffer"] += diff  # unspent stay money becomes savings
    alloc["stay"] = hotel.total_price

    return BudgetDecision(out, back, alternatives, hotel, hotel_alts, alloc, warnings)


def budget_lines(alloc: dict[str, int], days: list[Day], transport: int, stay: int) -> list[BudgetLine]:
    spent = {"transport": transport, "stay": stay, "food": 0, "activities": 0, "local": 0, "buffer": 0}
    for day in days:
        for s in day.slots:
            if s.kind == "meal":
                spent["food"] += s.cost
            elif s.kind == "place":
                spent["activities"] += s.cost
            elif s.kind == "travel":
                spent["local"] += s.cost
    order = ["transport", "stay", "food", "activities", "local", "buffer"]
    return [BudgetLine(key=k, label=LABELS[k], allocated=alloc[k], spent=spent[k]) for k in order]
