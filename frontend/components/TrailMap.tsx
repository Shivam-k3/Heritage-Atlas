"use client";

import React, { useEffect, useRef, useState } from "react";
import type { LayerGroup, Map as LeafletMap } from "leaflet";
import type { TrailStop } from "@/lib/types";

interface TrailMapProps {
  stops: TrailStop[];
}

function hasCoordinates(
  stop: TrailStop
): stop is TrailStop & { lat: number; lon: number } {
  return typeof stop.lat === "number" && typeof stop.lon === "number";
}

/**
 * Ordered map for a trail. Dashed lines are straight-line connections, not roads.
 */
export default function TrailMap({ stops }: TrailMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const layerRef = useRef<LayerGroup | null>(null);
  const [mapVersion, setMapVersion] = useState<number>(0);

  useEffect(() => {
    let isMounted = true;

    async function initMap() {
      if (!containerRef.current || mapRef.current) return;
      const L = await import("leaflet");
      if (!isMounted || !containerRef.current) return;

      const map = L.map(containerRef.current, {
        center: [24.8, 73.8],
        zoom: 6,
        zoomControl: false,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
      }).addTo(map);

      L.control.zoom({ position: "bottomright" }).addTo(map);

      mapRef.current = map;
      layerRef.current = L.layerGroup().addTo(map);
      setMapVersion((version) => version + 1);
    }

    void initMap();

    return () => {
      isMounted = false;
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
        layerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function drawRoute() {
      if (!mapRef.current || !layerRef.current) return;
      const L = await import("leaflet");
      if (!isMounted || !mapRef.current || !layerRef.current) return;

      const map = mapRef.current;
      const layer = layerRef.current;
      layer.clearLayers();

      const points = stops.filter(hasCoordinates);
      points.forEach((stop) => {
        const icon = L.divIcon({
          html: `<div style="width:28px;height:28px;border-radius:9999px;background:var(--indigo);color:var(--paper);display:flex;align-items:center;justify-content:center;font-family:var(--font-sans);font-weight:600;font-size:13px;border:2px solid var(--paper);box-shadow:0 2px 6px rgba(26,29,38,0.25)">${stop.stop_order}</div>`,
          className: "trail-stop-marker",
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });

        const marker = L.marker([stop.lat, stop.lon], { icon });
        marker.bindTooltip(`${stop.stop_order}. ${stop.site_name}`, {
          direction: "top",
        });
        layer.addLayer(marker);
      });

      if (points.length > 1) {
        layer.addLayer(
          L.polyline(
            points.map((stop) => [stop.lat, stop.lon]),
            {
              color: "#25305E",
              weight: 3,
              opacity: 0.8,
              dashArray: "6 6",
            }
          )
        );
        map.fitBounds(
          L.latLngBounds(points.map((stop) => [stop.lat, stop.lon])),
          { padding: [32, 32], maxZoom: 11 }
        );
      } else if (points.length === 1) {
        map.setView([points[0].lat, points[0].lon], 11);
      }
    }

    void drawRoute();

    return () => {
      isMounted = false;
    };
  }, [stops, mapVersion]);

  const mappableStops = stops.filter(hasCoordinates);

  return (
    <div className="relative w-full h-72 sm:h-96 border border-sandstone rounded-[6px] overflow-hidden">
      <div
        ref={containerRef}
        className="w-full h-full z-0 bg-stone"
        aria-label="Map of trail stops in order"
      />
      {mappableStops.length === 0 && (
        <div className="absolute inset-0 z-10 bg-stone flex items-center justify-center text-center p-6">
          <p className="type-small text-mute">
            No stops have coordinates, so no route can be drawn. Distances and
            legs are omitted rather than guessed.
          </p>
        </div>
      )}
    </div>
  );
}
