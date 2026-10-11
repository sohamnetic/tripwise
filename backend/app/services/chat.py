""""Ask Tripwise": a chat that suggests where to go and when, within a budget.

Google Gemini does the talking, but every number (season ratings, weather, costs) comes from the
tools below, which run Tripwise's own code (services/recommend.py). The suggestion cards the app
shows are built from those tool results, never from the model's text.

Without a Gemini key, past the daily cap, or if Gemini fails, "simple mode" reads month, budget,
group size, origin and interests from the message itself and answers from the same tools.
"""

import json
import logging
import re
import time
from datetime import date, timedelta

import httpx

from ..config import get_settings
from ..models.schemas import ChatReply, ChatTurn, Suggestion
from ..providers.base import _record_search, searches_today
from ..providers.geocode import UnknownCityError, _cities, resolve_city
from .recommend import MONTHS, destination_info, estimate_trip, find_destinations

log = logging.getLogger(__name__)
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_TOOL_ROUNDS = 4
MAX_CARDS = 4
# Vercel stops a request at 60s; leave room for simple mode and the database after Gemini.
AI_TIME_BUDGET_S = 40
HISTORY_TURNS = 12
TURN_CHARS = 600

INTERESTS = ["cool", "beaches", "mountains", "snow", "heritage", "spiritual", "wildlife", "backwaters", "cities", "abroad",
             "nature", "adventure", "food", "nightlife", "shopping"]
STYLES = ["budget", "balanced", "comfort", "luxury"]

TOOLS = [{"functionDeclarations": [
    {
        "name": "find_destinations",
        "description": "Best Tripwise destinations for a time of year, ranked by season (real weather data and "
                       "known closures), interests, budget fit and travel time. Returns rough cost ranges in INR "
                       "for the whole group. Use for any 'where should I go' question.",
        "parameters": {"type": "OBJECT", "properties": {
            "month": {"type": "INTEGER", "description": "Month of travel, 1–12. Omit if start_date is given."},
            "start_date": {"type": "STRING", "description": "Exact start date, YYYY-MM-DD, if known."},
            "nights": {"type": "INTEGER", "description": "Trip length in nights (default 4)."},
            "budget": {"type": "INTEGER", "description": "Total budget for everyone in INR, if the traveller gave one."},
            "travellers": {"type": "INTEGER", "description": "Number of people (default 2)."},
            "origin": {"type": "STRING", "description": "City they travel from, if known (e.g. Kolkata)."},
            "style": {"type": "STRING", "enum": STYLES, "description": "Travel style (default balanced)."},
            "interests": {"type": "ARRAY", "items": {"type": "STRING", "enum": INTERESTS},
                          "description": "What they want. 'cool' = escape the heat (ranks by actual temperature)."},
            "limit": {"type": "INTEGER", "description": "How many places, 1–6 (default 4)."},
        }},
    },
    {
        "name": "estimate_trip",
        "description": "Season rating and rough cost range (INR, whole group) for one specific destination. "
                       "Use for 'is X good in <month>?' or 'can I do X for ₹N?'.",
        "parameters": {"type": "OBJECT", "properties": {
            "destination": {"type": "STRING"},
            "origin": {"type": "STRING"},
            "month": {"type": "INTEGER"},
            "start_date": {"type": "STRING", "description": "YYYY-MM-DD"},
            "nights": {"type": "INTEGER"},
            "travellers": {"type": "INTEGER"},
            "style": {"type": "STRING", "enum": STYLES},
            "budget": {"type": "INTEGER"},
        }, "required": ["destination"]},
    },
    {
        "name": "destination_info",
        "description": "A destination's best months, known closures and what it's known for; optionally the "
                       "weather in one month. Use for 'when is the best time to visit X?'.",
        "parameters": {"type": "OBJECT", "properties": {
            "destination": {"type": "STRING"},
            "month": {"type": "INTEGER"},
        }, "required": ["destination"]},
    },
]}]


def system_prompt(today: date) -> str:
    return f"""You are Tripwise's travel assistant for Indian travellers. Today is {today:%A %d %B %Y}.
You help people choose where to go and when, within their budget, among the 101 destinations Tripwise covers.

Rules:
- For anything about seasons, weather, prices or budgets, call the tools. Never state a price, temperature
  or season rating that a tool didn't give you. Costs are rough estimates for the whole group: say "about"
  and that the planner (the "Plan this trip" button) gives exact prices.
- Only recommend destinations that the tools returned.
- The tool results say what each price covers ("for": people, nights, style). If they priced a shorter
  or budget-style trip than asked so it fits the budget, say so plainly.
- If no month or dates are given, assume next month and say so. If the budget or home city is missing,
  still suggest places, then ask one short question to narrow it down.
- Replies are read on phones: 2–4 short sentences, then a short list (place: why, about ₹ cost). The app
  shows a card with a "Plan this trip" button under your reply for each place, so don't repeat every detail.
- Write rupees as ₹ with Indian grouping (₹1,20,000). Be warm and concise; at most one emoji.
- Politely decline anything that isn't about travel. Never ask for personal details."""


# ---- tools ------------------------------------------------------------------------------------------

def _date(value) -> date | None:
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def _num(value, default=None):
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def run_tool(name: str, args: dict, today: date) -> tuple[dict, list[Suggestion]]:
    """Runs a tool. Returns (compact result for the model, suggestion cards for the app)."""
    common = dict(
        month=_num(args.get("month")), start=_date(args.get("start_date")), nights=_num(args.get("nights"), 4),
        travellers=_num(args.get("travellers"), 2), style=args.get("style") if args.get("style") in STYLES else "balanced",
        budget=_num(args.get("budget")), today=today,
    )
    try:
        if name == "find_destinations":
            found = find_destinations(origin=args.get("origin") or None, interests=list(args.get("interests") or []),
                                      limit=_num(args.get("limit"), 4), **common)
            return {"places": [_brief(s) for s in found]}, found
        if name == "estimate_trip":
            s = estimate_trip(args["destination"], origin=args.get("origin") or None, **common)
            return _brief(s), [s]
        if name == "destination_info":
            info = destination_info(args["destination"], _num(args.get("month")))
            # with a month, also show the place as a card so it can be planned in one tap
            card = [estimate_trip(args["destination"], **common)] if common["month"] else []
            return info, card
    except UnknownCityError as e:
        return {"error": str(e)}, []
    except (KeyError, ValueError) as e:
        return {"error": f"Bad arguments: {e}"}, []
    return {"error": f"Unknown tool {name}"}, []


def _brief(s: Suggestion) -> dict:
    """What the model needs to talk about a place (the cards carry the rest)."""
    c = s.cost
    return {
        "name": s.name, "known_for": s.tagline, "month": MONTHS[s.season.month - 1],
        "season": s.season.rating, "why": s.season.reason, "weather": s.season.weather, "note": s.season.note,
        "cost_inr": {"from": c.low, "to": c.high, "includes_travel": c.includes_travel,
                     "travel": c.transport_label or None, "fits_budget": c.fits_budget, "over_budget_by": c.over_by or None},
        "for": f"{c.travellers} people, {c.nights} nights, {c.style}",
    }


# ---- Gemini -------------------------------------------------------------------------------------------

class GeminiUnavailable(Exception):
    pass


def _gemini(contents: list[dict], today: date, timeout: float = 25) -> dict:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise GeminiUnavailable("no key")
    if settings.gemini_daily_limit and searches_today("gemini") >= settings.gemini_daily_limit:
        raise GeminiUnavailable("daily cap reached")
    _record_search("gemini")
    body = {
        "systemInstruction": {"parts": [{"text": system_prompt(today)}]},
        "contents": contents,
        "tools": TOOLS,
        "toolConfig": {"functionCallingConfig": {"mode": "AUTO"}},
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": 2048},
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(GEMINI_URL.format(model=settings.gemini_model), json=body,
                            headers={"x-goog-api-key": settings.gemini_api_key})
    except httpx.HTTPError as e:
        raise GeminiUnavailable(type(e).__name__) from None
    if r.status_code != 200:
        raise GeminiUnavailable(f"HTTP {r.status_code}: {r.text[:200]}")
    candidates = r.json().get("candidates") or []
    if not candidates or "content" not in candidates[0]:
        raise GeminiUnavailable("empty reply")
    return candidates[0]["content"]


def chat_with_gemini(history: list[ChatTurn], today: date) -> ChatReply:
    contents = [{"role": "user" if t.role == "user" else "model", "parts": [{"text": t.text}]} for t in history]
    cards: dict[str, Suggestion] = {}
    deadline = time.monotonic() + AI_TIME_BUDGET_S
    for _ in range(MAX_TOOL_ROUNDS):
        left = deadline - time.monotonic()
        if left < 3:
            raise GeminiUnavailable("out of time")
        content = _gemini(contents, today, timeout=min(25, left))
        parts = content.get("parts") or []
        calls = [p["functionCall"] for p in parts if "functionCall" in p]
        if not calls:
            text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
            if not text:
                raise GeminiUnavailable("no text")
            return ChatReply(reply=text, suggestions=list(cards.values())[-MAX_CARDS:], mode="ai")
        contents.append({"role": "model", "parts": parts})  # as sent, including any thought signatures
        responses = []
        for call in calls:
            result, found = run_tool(call.get("name", ""), call.get("args") or {}, today)
            for s in found:
                cards.pop(s.name, None)
                cards[s.name] = s  # latest last
            response = {"name": call.get("name", ""), "response": result}
            if call.get("id"):
                response["id"] = call["id"]  # newer models match answers to calls by id
            responses.append({"functionResponse": response})
        contents.append({"role": "user", "parts": responses})
    raise GeminiUnavailable("too many tool rounds")


# ---- simple mode ----------------------------------------------------------------------------------------

MONTH_WORDS = {m.lower(): i + 1 for i, m in enumerate(MONTHS)} | {m[:3].lower(): i + 1 for i, m in enumerate(MONTHS)} | {"sept": 9}
INTEREST_WORDS = [
    (r"beach|sea|coast|island", "beaches"), (r"snow|ski", "snow"), (r"hill|mountain|trek", "mountains"),
    (r"\bcool\b|\bcold\b|beat the heat|escape the heat|pleasant weather", "cool"),
    (r"temple|spiritual|pilgrim|holy|ghat", "spiritual"), (r"histor|heritage|fort|palace|monument", "heritage"),
    (r"wildlife|safari|tiger|jungle|national park", "wildlife"), (r"backwater|houseboat", "backwaters"),
    (r"\bcity|\bcities|nightlife|party|shopping", "cities"), (r"abroad|international|foreign|outside india|overseas", "abroad"),
]


# How each interest reads in a sentence ("Good hill picks for May").
INTEREST_NAMES = {"beaches": "beach", "mountains": "hill", "snow": "snow", "heritage": "heritage", "spiritual": "spiritual",
                  "wildlife": "wildlife", "backwaters": "backwater", "cities": "city", "abroad": "international", "cool": "cool"}


def _amount(num: str, unit: str) -> int:
    value = float(num.replace(",", ""))
    unit = unit.lower()
    if unit in ("k", "thousand"):
        value *= 1_000
    elif unit in ("l", "lakh", "lakhs", "lac", "lacs"):
        value *= 100_000
    return int(value)


def parse_request(text: str, today: date) -> dict:
    """Pulls trip details out of a plain message: 'Somewhere cool in May under ₹40k for 2 from Kolkata'."""
    t = text.lower()
    out: dict = {}

    m = re.search(r"(?:₹|rs\.?|inr)\s*([\d,.]+)\s*(k|thousand|l|lakhs?|lacs?)?\b"
                  r"|\b([\d,.]+)\s*(k|thousand|lakhs?|lacs?)\b"
                  r"|\b(?:under|below|budget(?: of)?|within|upto|up to)\s*([\d,]{4,})\b", t)
    if m:
        num, unit = (m.group(1), m.group(2) or "") if m.group(1) else (m.group(3), m.group(4)) if m.group(3) else (m.group(5), "")
        try:
            amount = _amount(num, unit)
            if 1000 <= amount <= 10_000_000:
                out["budget"] = amount
        except ValueError:
            pass

    for word, month in MONTH_WORDS.items():
        if re.search(rf"\b{word}\b", t):
            out["month"] = month
            break
    if "next month" in t:
        out["month"] = (today.month % 12) + 1
    elif "this month" in t:
        out["month"] = today.month

    if m := re.search(r"\b(\d{1,2})\s*(?:nights|night|days|day)\b", t):
        n = int(m.group(1))
        out["nights"] = max(1, n - 1 if "day" in m.group(0) else n)
    elif "long weekend" in t:
        out["nights"] = 3
    elif "weekend" in t:
        out["nights"] = 2
    elif "week" in t:
        out["nights"] = 6

    if m := re.search(r"family of (\d+)|\b(\d+)\s*(?:people|persons|adults|friends|of us|pax|travellers|travelers)|\bfor (\d+)\b", t):
        out["travellers"] = int(next(g for g in m.groups() if g))
    elif re.search(r"\bsolo\b|\balone\b|\bmyself\b", t):
        out["travellers"] = 1
    elif re.search(r"\bcouple\b|\bhoneymoon\b|\bwife\b|\bhusband\b|\bpartner\b", t):
        out["travellers"] = 2

    # "budget 1.5 lakh" is an amount, not a travel style
    if re.search(r"cheap|backpack|low[- ]cost|on a (?:tight )?budget|budget[- ](?:trip|travel|friendly|style|hotel)", t):
        out["style"] = "budget"
    elif re.search(r"luxury|5[- ]?star|five star|lavish", t):
        out["style"] = "luxury"
    elif re.search(r"comfort", t):
        out["style"] = "comfort"

    names = sorted(((c["name"], [c["name"].lower(), *c["aliases"]]) for c in _cities()), key=lambda c: -len(c[0]))
    if m := re.search(r"\bfrom\s+([a-z][a-z .]+)", t):
        after = m.group(1)
        for name, keys in names:
            if any(after.startswith(k) for k in keys):
                out["origin"] = name
                break
    for name, keys in names:
        if name == out.get("origin"):
            continue
        if any(re.search(rf"\b{re.escape(k)}\b", t) for k in keys):
            out["destination"] = name
            break

    out["interests"] = sorted({tag for pattern, tag in INTEREST_WORDS if re.search(pattern, t)})
    return out


def _fmt_inr(n: int) -> str:
    s = str(n)
    if len(s) <= 3:
        return f"₹{s}"
    head, tail = s[:-3], s[-3:]
    head = re.sub(r"(\d)(?=(\d{2})+$)", r"\1,", head)
    return f"₹{head},{tail}"


def chat_simple(history: list[ChatTurn], today: date) -> ChatReply:
    """No AI: read what we can from the conversation so far and answer from the tools."""
    asked: dict = {}
    for turn in history:  # later messages refine earlier ones ("make it ₹50k")
        if turn.role == "user":
            for k, v in parse_request(turn.text, today).items():
                if v:
                    asked[k] = v
    month = asked.get("month") or (today.month % 12) + 1
    common = dict(month=month, nights=asked.get("nights", 4), travellers=asked.get("travellers", 2),
                  style=asked.get("style", "balanced"), budget=asked.get("budget"), today=today)
    last = parse_request(history[-1].text, today)
    if last.get("destination") and not last.get("interests"):
        s = estimate_trip(last["destination"], origin=asked.get("origin"), **common)
        c = s.cost
        temps = s.season.weather.split(" · ")[0]
        reply = (f"**{s.name} in {MONTHS[month - 1]}: {s.season.rating.lower()}.** {s.season.reason}"
                 + ("." if temps in s.season.reason else f", {temps}.") + (f" {s.season.note}." if s.season.note else "") +
                 f"\n\nRough cost for {c.travellers}, {c.nights} nights: about {_fmt_inr(c.low)}–{_fmt_inr(c.high)}"
                 + ("" if c.includes_travel else " (plus travel; tell me your city)") + ".")
        return ChatReply(reply=reply, suggestions=[s], mode="simple")

    found = find_destinations(origin=asked.get("origin"), interests=asked.get("interests"), limit=MAX_CARDS, **common)
    what = f"{' & '.join(INTEREST_NAMES.get(i, i) for i in asked['interests'])} " if asked.get("interests") else ""
    within = f" within {_fmt_inr(asked['budget'])}" if asked.get("budget") else ""
    lines = [f"Good {what}picks for {MONTHS[month - 1]}{within}:"]
    if found and (found[0].cost.style != common["style"] or found[0].cost.nights != common["nights"]):
        c = found[0].cost
        lines[0] = (f"Nothing fits {_fmt_inr(asked['budget'])} as asked, so I've priced a {c.nights}-night "
                    f"{c.style}-style trip instead. Good {what}picks for {MONTHS[month - 1]}:")
    for s in found:
        lines.append(f"- **{s.name}**: {s.season.rating.lower()}, {s.season.weather}; about {_fmt_inr(s.cost.low)}–{_fmt_inr(s.cost.high)}")
    missing = [w for w, k in (("your budget", "budget"), ("your city", "origin"), ("the month", "month")) if k not in asked]
    if missing:
        ask = missing[0] if len(missing) == 1 else f"{', '.join(missing[:-1])} and {missing[-1]}"
        lines.append(f"\nTell me {ask} and I'll narrow it down.")
    return ChatReply(reply="\n".join(lines), suggestions=found, mode="simple")


# ---- entry point ------------------------------------------------------------------------------------------

def answer(messages: list[ChatTurn], today: date | None = None) -> ChatReply:
    today = today or date.today()
    history = [ChatTurn(role=t.role, text=t.text[:TURN_CHARS]) for t in messages[-HISTORY_TURNS:]]
    while history and history[0].role != "user":
        history.pop(0)  # Gemini wants the conversation to start with the traveller
    if not history or history[-1].role != "user":
        raise ValueError("The last message must be from the traveller.")
    try:
        return chat_with_gemini(history, today)
    except GeminiUnavailable as e:
        log.info("Gemini unavailable (%s); answering in simple mode", e)
        return chat_simple(history, today)
