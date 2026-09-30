// Trips this device has opened, newest first, so the installed app (which has no address bar or
// browser history) can reopen them. Stored only in this browser.
import type { Plan } from "../api/types";

const KEY = "tripwise:recent-trips";
const MAX = 8;

export interface RecentTrip {
  id: string;
  origin: string;
  destination: string;
  start: string;
  end: string;
  travellers: number;
  total: number;
  openedAt: number;
}

export function recentTrips(): RecentTrip[] {
  try {
    const list = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

function save(list: RecentTrip[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch {
    /* storage full or blocked: the list is a convenience, so carry on */
  }
}

export function rememberTrip(plan: Plan) {
  const entry: RecentTrip = {
    id: plan.id, origin: plan.origin.name, destination: plan.destination.name,
    start: plan.request.start_date, end: plan.request.end_date, travellers: plan.request.travellers,
    total: plan.summary.total_cost, openedAt: Date.now(),
  };
  save([entry, ...recentTrips().filter((t) => t.id !== plan.id)].slice(0, MAX));
}

export function forgetTrip(id: string) {
  save(recentTrips().filter((t) => t.id !== id));
}
