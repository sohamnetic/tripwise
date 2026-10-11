// The planner form as it was last submitted on this device, so it opens pre-filled.
import type { TripRequest } from "../api/types";

export const LAST_KEY = "tripwise:last-request";

export function loadLast(): TripRequest | null {
  try {
    const raw = localStorage.getItem(LAST_KEY);
    return raw ? (JSON.parse(raw) as TripRequest) : null;
  } catch {
    return null;
  }
}
