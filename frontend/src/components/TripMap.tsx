import L from "leaflet";
import { Fragment } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer } from "react-leaflet";
import type { Day, Hotel } from "../api/types";
import { dayColor } from "../lib/format";

function pin(color: string, text: string, size = 26) {
  return L.divIcon({
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `<div style="background:${color};width:${size}px;height:${size}px;border-radius:9999px;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.35);display:grid;place-items:center;color:white;font:700 11px 'Plus Jakarta Sans',sans-serif">${text}</div>`,
  });
}

export default function TripMap({ days, hotel, activeDay }: { days: Day[]; hotel: Hotel; activeDay: number | null }) {
  const stops = days.map((d) => ({
    day: d,
    points: d.slots.filter((s) => s.kind === "place" && s.lat != null && s.lng != null),
  }));
  const all: [number, number][] = [[hotel.lat, hotel.lng], ...stops.flatMap((s) => s.points.map((p) => [p.lat!, p.lng!] as [number, number]))];
  const bounds = L.latLngBounds(all).pad(0.15);

  return (
    <MapContainer bounds={bounds} scrollWheelZoom={false} className="h-[420px] w-full rounded-2xl" key={activeDay ?? "all"}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Marker position={[hotel.lat, hotel.lng]} icon={pin("#0f172a", "🏨", 32)}>
        <Popup>
          <b>{hotel.name}</b>
          <br />
          Your stay
        </Popup>
      </Marker>
      {stops.map(({ day, points }) => {
        const faded = activeDay !== null && activeDay !== day.number;
        const color = faded ? "#cbd5e1" : dayColor(day.number);
        return (
          <Fragment key={day.number}>
            {points.length > 0 && (
              <Polyline
                positions={[[hotel.lat, hotel.lng], ...points.map((p) => [p.lat!, p.lng!] as [number, number]), [hotel.lat, hotel.lng]]}
                pathOptions={{ color, weight: faded ? 2 : 3, opacity: faded ? 0.5 : 0.85, dashArray: "6 6" }}
              />
            )}
            {points.map((p, i) => (
              <Marker key={p.ref_id} position={[p.lat!, p.lng!]} icon={pin(color, `${i + 1}`)} zIndexOffset={faded ? 0 : 500}>
                <Popup>
                  <b>{p.title}</b>
                  <br />
                  Day {day.number}, stop {i + 1} · {p.start}
                </Popup>
              </Marker>
            ))}
          </Fragment>
        );
      })}
    </MapContainer>
  );
}
