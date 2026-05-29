import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  CircleMarker,
  Popup,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import type { GeoJSON as GeoJSONType } from "../api/client";
import { api } from "../api/client";
import "leaflet/dist/leaflet.css";
import type { Layer, LeafletMouseEvent } from "leaflet";

const TYPE_COLORS: Record<string, string> = {
  Clinic: "#3b82f6",
  "Clinic with Maternity": "#6366f1",
  "Health Post": "#10b981",
  "Primary Hospital": "#f59e0b",
  "District Hospital": "#ef4444",
  "Referral Hospital": "#dc2626",
  Warehouse: "#8b5cf6",
};

// Color scale for choropleth
function facilityColor(count: number): string {
  if (count >= 50) return "#0ea5e9";
  if (count >= 30) return "#38bdf8";
  if (count >= 20) return "#7dd3fc";
  if (count >= 10) return "#bae6fd";
  return "#e0f2fe";
}

function FitBounds({ geojson }: { geojson: any }) {
  const map = useMap();
  useEffect(() => {
    if (!geojson) return;
    const layer = L.geoJSON(geojson);
    const bounds = layer.getBounds();
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [20, 20] });
    }
  }, [geojson, map]);
  return null;
}

interface Props {
  height?: string;
  showFacilities?: boolean;
}

export default function BotswanaMap({
  height = "500px",
  showFacilities = true,
}: Props) {
  const [districts, setDistricts] = useState<any>(null);
  const [facilities, setFacilities] = useState<GeoJSONType | null>(null);

  useEffect(() => {
    api.getDistrictsGeoJSON().then(setDistricts).catch(console.error);
    if (showFacilities) {
      api.getFacilitiesGeoJSON().then(setFacilities).catch(console.error);
    }
  }, [showFacilities]);

  if (!districts) return <div className="loading">Loading map...</div>;

  const districtStyle = (feature: any) => {
    const count = feature?.properties?.facility_count ?? 0;
    return {
      fillColor: facilityColor(count),
      fillOpacity: 0.25,
      color: "#38bdf8",
      weight: 1,
      opacity: 0.5,
    };
  };

  const onEachDistrict = (feature: any, layer: Layer) => {
    const props = feature.properties || {};
    const name = props.shapeName || "Unknown";
    const count = props.facility_count ?? 0;
    layer.bindPopup(
      `<strong>${name}</strong><br/>${count} health facilities`
    );
    layer.on({
      mouseover: (e: LeafletMouseEvent) => {
        e.target.setStyle({ fillOpacity: 0.5, weight: 2 });
      },
      mouseout: (e: LeafletMouseEvent) => {
        e.target.setStyle({ fillOpacity: 0.25, weight: 1 });
      },
    });
  };

  return (
    <MapContainer
      center={[-22.3, 24.7]}
      zoom={6}
      style={{ height, width: "100%", borderRadius: "12px", background: "#0b1120" }}
      attributionControl={false}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://carto.com">CARTO</a>'
      />
      <GeoJSON data={districts} style={districtStyle} onEachFeature={onEachDistrict} />
      <FitBounds geojson={districts} />

      {showFacilities &&
        facilities?.features.map((f, i) => (
          <CircleMarker
            key={i}
            center={[
              f.geometry.coordinates[1],
              f.geometry.coordinates[0],
            ]}
            radius={3}
            fillColor={TYPE_COLORS[f.properties.type] || "#6b7280"}
            fillOpacity={0.9}
            stroke={false}
          >
            <Popup>
              <strong>{f.properties.name}</strong>
              <br />
              {f.properties.type}
              <br />
              <em>{f.properties.dhmt}</em>
            </Popup>
          </CircleMarker>
        ))}
    </MapContainer>
  );
}
