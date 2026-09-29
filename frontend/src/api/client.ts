import { useQuery } from "@tanstack/react-query";
import type { City, Health, JobStatus, Plan, TripRequest } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      /* not JSON */
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/api/health"),
  cities: (q: string) => request<City[]>(`/api/cities?q=${encodeURIComponent(q)}`),
  createTrip: (body: TripRequest) =>
    request<{ job_id: string }>("/api/trips", { method: "POST", body: JSON.stringify(body) }),
  job: (id: string) => request<JobStatus>(`/api/jobs/${id}`),
  trip: (id: string) => request<Plan>(`/api/trips/${id}`),
};

export function useHealth() {
  return useQuery({ queryKey: ["health"], queryFn: api.health, staleTime: 60_000 });
}

export function useCities(q: string) {
  return useQuery({ queryKey: ["cities", q], queryFn: () => api.cities(q), staleTime: Infinity });
}

export function useJob(id: string) {
  return useQuery({
    queryKey: ["job", id],
    queryFn: () => api.job(id),
    refetchInterval: (q) => (q.state.data && ["done", "error"].includes(q.state.data.status) ? false : 1000),
  });
}

export function useTrip(id: string) {
  return useQuery({ queryKey: ["trip", id], queryFn: () => api.trip(id), staleTime: Infinity });
}
