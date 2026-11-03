import { useEffect, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup } from "react-leaflet";
import { api } from "../api/client";
import type { Facility } from "../api/client";
import { useTheme } from "../theme";
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
  // District outlines give the region's facilities a country to sit in.
  const [districts, setDistricts] = useState<any>(null);
  useEffect(() => {
    api.getDistrictsGeoJSON().then(setDistricts).catch(console.error);
  }, []);

  const theme = useTheme();

  if (!facilities.length) return null;

  const light = theme === "light";
  const outline = light ? "#0369a1" : "#38bdf8";

  const center: [number, number] = [
    facilities.reduce((s, f) => s + f.latitude, 0) / facilities.length,
    facilities.reduce((s, f) => s + f.longitude, 0) / facilities.length,
  ];

  return (
    <MapContainer
      center={center}
      zoom={9}
      style={{ height: "450px", width: "100%", borderRadius: "8px", background: light ? "#eef3f9" : "#0b1120" }}
    >
      <TileLayer
        maxNativeZoom={light ? 19 : 16}
        attribution={light
          ? '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          : 'Tiles &copy; <a href="https://www.esri.com">Esri</a>'}
        key={theme}
        url={light
          ? "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          : "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"}
      />
      {districts && (
        <GeoJSON
          data={districts}
          interactive={false}
          style={{ fillColor: outline, fillOpacity: light ? 0.1 : 0.08, color: outline, weight: 1, opacity: light ? 0.8 : 0.5 }}
        />
      )}
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
