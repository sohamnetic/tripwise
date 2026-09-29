const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export const rupees = (n: number) => inr.format(n);

export function duration(min: number) {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? `${h}h${m ? ` ${m}m` : ""}` : `${m}m`;
}

export function time(iso: string) {
  return new Date(iso).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });
}

export function shortDate(iso: string) {
  return new Date(iso.length === 10 ? `${iso}T00:00:00` : iso).toLocaleDateString("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

// Local YYYY-MM-DD. (toISOString() would convert to UTC and shift the date in India.)
function localIso(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function addDays(iso: string, days: number) {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + days);
  return localIso(d);
}

export function todayPlus(days: number) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return localIso(d);
}

// One colour per day on the map and itinerary.
export const DAY_COLORS = ["#0d8573", "#f06a4f", "#6d5bd0", "#c7801a", "#2f7fd8", "#c2417a", "#4b8f29", "#8a5a44"];
export const dayColor = (n: number) => DAY_COLORS[(n - 1) % DAY_COLORS.length];

export const MODE_ICON: Record<string, string> = { flight: "✈️", train: "🚆", bus: "🚌" };
