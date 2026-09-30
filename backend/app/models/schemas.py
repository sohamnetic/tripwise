"""API-facing Pydantic models. Every price is in INR (whole rupees)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Style = Literal["budget", "balanced", "comfort", "luxury"]
Mode = Literal["flight", "train", "bus"]
TransportPref = Literal["any", "flight", "train", "bus"]
Interest = Literal["beaches", "food", "history", "nightlife", "nature", "shopping", "adventure"]


class TripRequest(BaseModel):
    origin: str = Field(min_length=2, max_length=80)
    destination: str = Field(min_length=2, max_length=80)
    start_date: date
    end_date: date
    travellers: int = Field(ge=1, le=10)
    budget: int = Field(ge=1000, le=10_000_000, description="Total trip budget in INR")
    style: Style = "balanced"
    interests: list[Interest] = []
    transport: TransportPref = "any"
    # Upgrades the traveller chose from the "spend your savings" suggestions.
    hotel_id: str | None = None
    transport_ids: list[str] = Field(default=[], max_length=2)  # [outbound id, return id]
    must_include: list[str] = Field(default=[], max_length=20)  # place ids
    treat_dinners: bool = False  # dinners at the best-rated places nearby, whatever the price

    @model_validator(mode="after")
    def check_dates(self):
        nights = (self.end_date - self.start_date).days
        if nights < 1:
            raise ValueError("end_date must be at least one day after start_date")
        if nights > 14:
            raise ValueError("trips longer than 14 nights are not supported yet")
        return self

    @property
    def nights(self) -> int:
        return (self.end_date - self.start_date).days


class Link(BaseModel):
    label: str
    url: str


class CityOption(BaseModel):
    """A city for the search box: enough to find it by any of its names."""
    name: str
    state: str
    country: str
    aliases: list[str] = []


class City(BaseModel):
    name: str
    state: str
    country: str
    lat: float
    lng: float
    iata: str
    has_rail: bool
    has_road: bool
    international: bool


class TransportOption(BaseModel):
    id: str
    mode: Mode
    carrier: str
    service: str  # flight number, train class, bus type
    from_city: str
    to_city: str
    depart: datetime
    arrive: datetime
    duration_min: int
    price_per_person: int
    total_price: int
    is_estimate: bool
    links: list[Link] = []


class Hotel(BaseModel):
    id: str
    name: str
    area: str
    rating: float
    reviews: int
    stars: int
    nightly_price: int  # per room
    lat: float
    lng: float
    amenities: list[str] = []
    rooms: int = 1
    total_price: int = 0
    links: list[Link] = []
    is_estimate: bool = False  # a typical price for this kind of stay, not a real listing


class Place(BaseModel):
    id: str
    name: str
    category: str
    area: str
    rating: float
    lat: float
    lng: float
    fee_per_person: int
    fee_is_estimate: bool = True
    duration_min: int
    hours: str
    description: str
    links: list[Link] = []
    # False for open data (Wikidata, OpenStreetMap), where `rating` is only our ranking by how
    # well known the place is: it's used for choosing, never shown as a star rating.
    rating_known: bool = True


class Restaurant(BaseModel):
    id: str
    name: str
    cuisine: str
    area: str
    rating: float
    lat: float
    lng: float
    cost_per_person: int
    links: list[Link] = []
    rating_known: bool = True


class Slot(BaseModel):
    kind: Literal["place", "meal", "travel", "checkin", "checkout", "arrival", "departure"]
    start: str  # "HH:MM"
    end: str
    title: str
    ref_id: str | None = None
    cost: int = 0  # for the whole group
    is_estimate: bool = False
    lat: float | None = None
    lng: float | None = None
    notes: str = ""


class Day(BaseModel):
    number: int
    date: date
    title: str
    slots: list[Slot]
    cost: int


class BudgetLine(BaseModel):
    key: Literal["transport", "stay", "food", "activities", "local", "buffer"]
    label: str
    allocated: int
    spent: int


class Package(BaseModel):
    provider: str
    title: str
    url: str


class TripOverrides(BaseModel):
    hotel_id: str | None = None
    transport_ids: list[str] = []
    must_include: list[str] = []
    treat_dinners: bool = False


class Upgrade(BaseModel):
    """A way to spend leftover budget. `extra_cost` is exactly what applying it adds to the total."""
    id: str
    kind: Literal["hotel", "activity", "transport", "dining"]
    title: str
    detail: str
    extra_cost: int
    apply: TripOverrides


class Summary(BaseModel):
    budget: int
    total_cost: int
    remaining: int
    within_budget: bool
    per_person: int
    nights: int
    rooms: int


class Plan(BaseModel):
    id: str
    request: TripRequest
    origin: City
    destination: City
    created_at: datetime
    prices_checked_at: datetime
    data_mode: Literal["demo", "live"]
    planned_by: Literal["ai", "rules"] = "rules"
    summary: Summary
    budget: list[BudgetLine]
    outbound: TransportOption
    inbound: TransportOption
    transport_alternatives: list[TransportOption]
    hotel: Hotel
    hotel_alternatives: list[Hotel]
    days: list[Day]
    places: list[Place]
    packages: list[Package]
    checklist: list[Link]
    upgrades: list[Upgrade] = []
    warnings: list[str] = []
    tips: list[str] = []
    credits: list[Link] = []  # open data sources used for this plan (their licences ask for credit)


class JobStatus(BaseModel):
    id: str
    status: Literal["queued", "running", "done", "error"]
    step: str
    progress: int  # 0-100
    trip_id: str | None = None
    error: str | None = None


class JobCreated(BaseModel):
    job_id: str
