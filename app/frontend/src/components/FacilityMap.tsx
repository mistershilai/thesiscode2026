import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import type { Facility } from "../api/client";
import "leaflet/dist/leaflet.css";

const TYPE_COLORS: Record<string, string> = {
  Clinic: "#3b82f6",
  "Clinic with Maternity": "#6366f1",
  "Health Post": "#10b981",
  "Primary Hospital": "#f59e0b",
  "District Hospital": "#ef4444",
  "Referral Hospital": "#dc2626",
};

interface Props {
  facilities: Facility[];
}

export default function FacilityMap({ facilities }: Props) {
  if (!facilities.length) return null;

  const center: [number, number] = [
    facilities.reduce((s, f) => s + f.latitude, 0) / facilities.length,
    facilities.reduce((s, f) => s + f.longitude, 0) / facilities.length,
  ];

  return (
    <MapContainer
      center={center}
      zoom={9}
      style={{ height: "450px", width: "100%", borderRadius: "8px" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://carto.com">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      {facilities.map((f) => (
        <CircleMarker
          key={f.name}
          center={[f.latitude, f.longitude]}
          radius={6}
          fillColor={TYPE_COLORS[f.type] || "#6b7280"}
          fillOpacity={0.85}
          stroke={true}
          weight={1}
          color="#fff"
        >
          <Popup>
            <strong>{f.name}</strong>
            <br />
            {f.type}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
