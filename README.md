# Tripwise: budget trip planner

Enter where you're going and how much you can spend. Tripwise builds the whole trip:
- transport there and back
- a stay that fits the budget
- a day-by-day itinerary with entry fees, meals and local travel
- a map of every stop
- one checklist of links to book each piece on real sites (MakeMyTrip, Booking.com, IRCTC, redBus, Klook…)

India-first, all prices in ₹.

## Features

- An animated scene for each destination (beach, hills, heritage, riverside, city) that changes as you type
- A loading screen with a plane flying from origin to destination, plus rotating travel tips
- Plan page:
  - totals that count up
  - a budget donut chart
  - transport and hotel picks
  - a colour-coded day-by-day plan, grouped by area, with a map
- **"You're saving ₹X" card:** leftover budget stays as savings unless you choose to spend it.
  - Suggestions: activities that didn't fit, nicer dinners, a better hotel, faster or comfier transport.
  - Each one is priced by re-planning with it applied, so "+₹1,120" is exactly what the total changes by. Any stop it would replace is named.
  - "Add to my trip" applies it; your picks show as chips you can remove.
- Weather forecast for your actual dates via Open-Meteo (free, no key): the daily forecast up to about 2 weeks out, the ECMWF long-range forecast up to about 7 months (chance of rain from 51 forecast runs), and a clear note beyond that
- A packing list built from destination, season, interests and transport
- A booking checklist (confetti when everything's booked) and package suggestions
- "Cheaper version" / "More comfort" one-click replanning, a share link and print-to-PDF

## How it works

```
React (Vite + TS)  ──/api──▶  FastAPI
                                ├─ providers/  transport, hotels & places, city lookup
                                ├─ services/budget.py     fits everything to the budget (plain Python)
                                ├─ services/scheduler.py  day-by-day plan, grouped by area
                                ├─ services/links.py      deep links to booking sites
                                └─ SQLite                 saved trips + background jobs
```

**Design rule:** every rupee shown is computed in Python from provider data. The AI step, when enabled, only picks and orders places we already fetched. It never invents prices or hotels.

Planning runs as a background job. The frontend polls `GET /api/jobs/{id}` for progress and then opens `/trip/{id}`, a shareable link.

## Data sources

| What | Source | Status |
|---|---|---|
| Flights | SerpApi Google Flights | Live mode; typical-fare estimates when a live search isn't possible. Simulated in demo mode |
| Hotels, attractions, restaurants | SerpApi Google Hotels / Google Maps | Live mode. `backend/fixtures/*.json` in demo mode |
| Attractions, restaurants (free fallback) | Wikidata + Wikivoyage (sights), OpenStreetMap via Geoapify (beaches, restaurants) | Used when Google results aren't available. No star ratings, so none are shown |
| Trains, buses | Distance-based fare estimates plus IRCTC / redBus links | Always an **estimate**, because there is no public IRCTC or redBus API |
| Map | Leaflet + OpenStreetMap | Free, no key |

## Run it locally

**Backend** (Python 3.10+)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env        # macOS/Linux: cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

**Frontend** (Node 20.19+)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

**Tests**

```bash
cd backend
.venv\Scripts\python -m pytest -q
```

## Demo mode

With `DEMO_MODE=true` (the default), no paid API is called. Demo data covers **Goa** as the destination; any city in `backend/app/data/cities.json` works as the origin. Demo prices are sample values and are labelled "sample" in the UI. Hotel and restaurant names in the demo data are fictional.

To add another demo destination, drop a `backend/fixtures/<city>.json` file with the same shape as `goa.json`.

## Deploy (all free, no card)

| Part | Service | Settings |
|---|---|---|
| Database | Neon Postgres | copy the pooled connection string |
| API | Vercel project, Root Directory `backend` | FastAPI is detected from `app/main.py`. Env: `DEMO_MODE=false`, `SERPAPI_KEY`, `DATABASE_URL`, `CORS_ORIGINS` |
| Website | Vercel project, Root Directory `frontend` | Vite. Env: `VITE_API_URL` = the API project's URL |

### Staying within the free SerpApi quota

- **Daily cap.** At most `SERPAPI_DAILY_LIMIT` live searches a day (default 8 ≈ 250/month).
- **Fallbacks.** When a live search isn't possible (cap reached, month used up, SerpApi down):
  - flights and hotels show typical prices, marked "estimate", with a warning on the plan
  - sights and restaurants use a saved Google copy (kept 30 days, usable up to 90), else free open data
- **Per-visitor limits.** Each visitor (told apart by a hash of their IP) gets `VISITOR_DAILY_TRIPS` new trips a day (default 5). Replanning the same trip doesn't count toward that, but everything counts toward `VISITOR_DAILY_REQUESTS` (default 40).

On Vercel (`VERCEL=1`) trip planning runs inside the request instead of in the background, because serverless functions may stop after responding. Locally it runs in the background and the loading screen shows real progress.

## Roadmap

- [x] Step 1: skeleton, demo data end to end, budget engine, scheduler, plan UI, map, booking checklist
- [ ] Step 2: live SerpApi flights, hotels and places, with an SQLite cache (6–12h TTL)
- [ ] Step 3: Claude picks and orders places (structured output, validated against fetched IDs)
- [ ] Step 5: regenerate with a new budget, deploy (Vercel + Render + Neon)

## Known limitations

- Train and bus fares are estimates, and the IRCTC link opens the search page (it can't be pre-filled).
- Opening hours are read from simple "HH:MM–HH:MM" strings. Seasonal closures are shown but not enforced.
