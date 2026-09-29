// Mirrors backend/app/models/schemas.py

export type Style = "budget" | "balanced" | "comfort";
export type Mode = "flight" | "train" | "bus";
export type TransportPref = "any" | Mode;
export type Interest = "beaches" | "food" | "history" | "nightlife" | "nature" | "shopping" | "adventure";

export interface TripRequest {
  origin: string;
  destination: string;
  start_date: string;
  end_date: string;
  travellers: number;
  budget: number;
  style: Style;
  interests: Interest[];
  transport: TransportPref;
  // upgrades picked from the "you're saving" suggestions
  hotel_id?: string | null;
  transport_ids?: string[];
  must_include?: string[];
  treat_dinners?: boolean;
}

export interface TripOverrides {
  hotel_id: string | null;
  transport_ids: string[];
  must_include: string[];
  treat_dinners: boolean;
}

export interface Upgrade {
  id: string;
  kind: "hotel" | "activity" | "transport" | "dining";
  title: string;
  detail: string;
  extra_cost: number;
  apply: TripOverrides;
}

export interface Link {
  label: string;
  url: string;
}

export interface City {
  name: string;
  state: string;
  country: string;
  lat: number;
  lng: number;
  iata: string;
  has_rail: boolean;
  has_road: boolean;
  international: boolean;
}

export interface TransportOption {
  id: string;
  mode: Mode;
  carrier: string;
  service: string;
  from_city: string;
  to_city: string;
  depart: string;
  arrive: string;
  duration_min: number;
  price_per_person: number;
  total_price: number;
  is_estimate: boolean;
  links: Link[];
}

export interface Hotel {
  id: string;
  name: string;
  area: string;
  rating: number;
  reviews: number;
  stars: number;
  nightly_price: number;
  lat: number;
  lng: number;
  amenities: string[];
  rooms: number;
  total_price: number;
  links: Link[];
}

export interface Place {
  id: string;
  name: string;
  category: string;
  area: string;
  rating: number;
  lat: number;
  lng: number;
  fee_per_person: number;
  fee_is_estimate: boolean;
  duration_min: number;
  hours: string;
  description: string;
  links: Link[];
}

export type SlotKind = "place" | "meal" | "travel" | "checkin" | "checkout" | "arrival" | "departure";

export interface Slot {
  kind: SlotKind;
  start: string;
  end: string;
  title: string;
  ref_id: string | null;
  cost: number;
  is_estimate: boolean;
  lat: number | null;
  lng: number | null;
  notes: string;
}

export interface Day {
  number: number;
  date: string;
  title: string;
  slots: Slot[];
  cost: number;
}

export type BudgetKey = "transport" | "stay" | "food" | "activities" | "local" | "buffer";

export interface BudgetLine {
  key: BudgetKey;
  label: string;
  allocated: number;
  spent: number;
}

export interface Package {
  provider: string;
  title: string;
  url: string;
}

export interface Plan {
  id: string;
  request: TripRequest;
  origin: City;
  destination: City;
  created_at: string;
  prices_checked_at: string;
  data_mode: "demo" | "live";
  planned_by: "ai" | "rules";
  summary: {
    budget: number;
    total_cost: number;
    remaining: number;
    within_budget: boolean;
    per_person: number;
    nights: number;
    rooms: number;
  };
  budget: BudgetLine[];
  outbound: TransportOption;
  inbound: TransportOption;
  transport_alternatives: TransportOption[];
  hotel: Hotel;
  hotel_alternatives: Hotel[];
  days: Day[];
  places: Place[];
  packages: Package[];
  checklist: Link[];
  upgrades: Upgrade[];
  warnings: string[];
  tips: string[];
}

export interface JobStatus {
  id: string;
  status: "queued" | "running" | "done" | "error";
  step: string;
  progress: number;
  trip_id: string | null;
  error: string | null;
}

export interface Health {
  ok: boolean;
  demo_mode: boolean;
  demo_destinations: string[];
}
