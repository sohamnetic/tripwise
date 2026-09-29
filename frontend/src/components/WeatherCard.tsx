import { useQuery } from "@tanstack/react-query";
import type { City } from "../api/types";

// Forecasts for the trip dates themselves, from Open-Meteo (free, no key):
//  - up to ~15 days ahead: the normal daily forecast
//  - up to ~7 months ahead: the ECMWF seasonal forecast. It has 51 runs per day, so we
//    report the average temperature and the share of runs with rain as "chance of rain".
//  - further out: say so, rather than show old data.
const DAILY_FORECAST_DAYS = 15;
const RAIN_MM = 1;

interface DayWeather {
  date: string;
  max: number;
  min: number;
  rainChance: number; // 0-100
  code?: number; // WMO weather code (daily forecast only)
}

type Weather =
  | { kind: "daily" | "seasonal"; days: DayWeather[] }
  | { kind: "unavailable" };

const dayLabel = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { weekday: "short", day: "numeric" });

function iconFor(d: DayWeather) {
  const c = d.code;
  if (c !== undefined) {
    if (c >= 95) return "⛈️";
    if ((c >= 71 && c <= 77) || c === 85 || c === 86) return "🌨️";
    if (c >= 51 || d.rainChance >= 60) return d.rainChance >= 60 ? "🌧️" : "🌦️";
    if (c === 45 || c === 48) return "🌫️";
    if (c === 3) return "☁️";
    return c === 0 ? "☀️" : "🌤️";
  }
  if (d.max <= 2) return "🌨️";
  if (d.rainChance >= 60) return "🌧️";
  if (d.rainChance >= 30) return "🌦️";
  return d.max >= 30 ? "☀️" : "🌤️";
}

const avg = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;

async function fetchWeather(city: City, start: string, end: string): Promise<Weather> {
  const daysUntilEnd = Math.round((Date.parse(end) - Date.now()) / 86_400_000);
  const base = { latitude: String(city.lat), longitude: String(city.lng), timezone: "auto", start_date: start, end_date: end };

  if (daysUntilEnd <= DAILY_FORECAST_DAYS) {
    const params = new URLSearchParams({ ...base, daily: "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max" });
    const res = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`);
    if (!res.ok) throw new Error("forecast unavailable");
    const { daily } = await res.json();
    return {
      kind: "daily",
      days: daily.time.map((date: string, i: number) => ({
        date,
        max: daily.temperature_2m_max[i],
        min: daily.temperature_2m_min[i],
        rainChance: daily.precipitation_probability_max[i] ?? 0,
        code: daily.weather_code[i],
      })),
    };
  }

  const params = new URLSearchParams({ ...base, daily: "temperature_2m_max,temperature_2m_min,precipitation_sum" });
  const res = await fetch(`https://seasonal-api.open-meteo.com/v1/seasonal?${params}`);
  const data = await res.json();
  if (!res.ok || data.error) return { kind: "unavailable" };

  // every key like "temperature_2m_max", "temperature_2m_max_member01", ... is one run
  const runs = (prefix: string) =>
    Object.entries(data.daily as Record<string, (number | null)[]>).filter(([k]) => k === prefix || k.startsWith(`${prefix}_member`)).map(([, v]) => v);
  const maxRuns = runs("temperature_2m_max");
  const minRuns = runs("temperature_2m_min");
  const rainRuns = runs("precipitation_sum");
  const days = (data.daily.time as string[]).map((date, i) => {
    const vals = (rs: (number | null)[][]) => rs.map((r) => r[i]).filter((v): v is number => v != null);
    const rain = vals(rainRuns);
    return {
      date,
      max: avg(vals(maxRuns)),
      min: avg(vals(minRuns)),
      rainChance: rain.length ? (rain.filter((mm) => mm >= RAIN_MM).length / rain.length) * 100 : 0,
    };
  });
  if (days.some((d) => Number.isNaN(d.max))) return { kind: "unavailable" };
  return { kind: "seasonal", days };
}

export default function WeatherCard({ city, start, end }: { city: City; start: string; end: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["weather", city.name, start, end],
    queryFn: () => fetchWeather(city, start, end),
    staleTime: 60 * 60_000,
    retry: 0,
  });

  if (isError) return null;
  if (isLoading || !data) return <div className="card h-[132px] skeleton" aria-label="Loading weather" />;

  if (data.kind === "unavailable")
    return (
      <div className="card p-4">
        <div className="font-bold">🌦️ Weather forecast</div>
        <p className="mt-1 text-sm text-muted">
          Your trip is more than about 7 months away, beyond what forecasts can see. A long-range forecast will appear here once your dates come into range.
        </p>
      </div>
    );

  const days = data.days;
  const hi = Math.round(Math.max(...days.map((d) => d.max)));
  const lo = Math.round(Math.min(...days.map((d) => d.min)));
  const wet = days.filter((d) => d.rainChance >= 50).length;
  const clothes = hi >= 32 ? "Light cottons, sunscreen and a cap." : lo <= 8 ? "Pack warm layers, it gets cold." : lo <= 16 ? "A light jacket for evenings." : "Comfortable summer clothes.";
  const hint = wet * 2 >= days.length ? `${clothes} Carry an umbrella or rain jacket.` : clothes;

  return (
    <div className="card p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="font-bold">
          {data.kind === "daily" ? "🌦️ Weather forecast" : "🌦️ Long-range forecast"}
        </div>
        <div className="text-sm text-muted">
          {lo}–{hi}°C · {wet ? `rain likely on ${wet} of ${days.length} days` : "mostly dry"}
        </div>
      </div>
      <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
        {days.map((d) => (
          <div key={d.date} className="min-w-[68px] flex-1 rounded-xl bg-paper px-2 py-2 text-center">
            <div className="text-[11px] font-semibold text-muted">{dayLabel(d.date)}</div>
            <div className="my-0.5 text-2xl">{iconFor(d)}</div>
            <div className="text-xs font-bold">
              {Math.round(d.max)}°<span className="font-medium text-muted"> / {Math.round(d.min)}°</span>
            </div>
            <div className="mt-0.5 text-[11px] text-sky-700">💧 {Math.round(d.rainChance / 10) * 10}%</div>
          </div>
        ))}
      </div>
      <p className="mt-2 text-xs text-muted">
        👕 {hint}{" "}
        {data.kind === "seasonal" && "Long-range forecasts show the general trend, not exact days. A day-by-day forecast replaces this about 2 weeks before you travel."}
      </p>
    </div>
  );
}
