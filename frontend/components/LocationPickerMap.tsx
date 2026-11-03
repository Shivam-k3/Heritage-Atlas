"use client";

import React, { useEffect, useRef } from "react";
import type { Map as LeafletMap, Marker as LeafletMarker } from "leaflet";

interface LocationPickerMapProps {
  lat: number | null;
  lon: number | null;
  onChange: (lat: number, lon: number) => void;
}

export default function LocationPickerMap({
  lat,
  lon,
  onChange,
}: LocationPickerMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const markerRef = useRef<LeafletMarker | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function initMap() {
      if (!containerRef.current || mapRef.current) return;
      const L = await import("leaflet");
      if (!isMounted || !containerRef.current) return;

      const defaultLat = lat ?? 24.5;
      const defaultLon = lon ?? 73.5;

      const map = L.map(containerRef.current, {
        center: [defaultLat, defaultLon],
        zoom: lat && lon ? 11 : 6,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
      }).addTo(map);

      // Custom pin icon
      const pinIcon = L.divIcon({
        html: `
          <div style="display:flex;flex-direction:column;align-items:center;">
            <div style="width:28px;height:28px;border-radius:9999px;background:var(--indigo);border:2px solid var(--sandstone);box-shadow:0 2px 6px rgba(26,29,38,0.3);display:flex;align-items:center;justify-content:center;color:#F7F8F5;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="12" cy="12" r="3"/></svg>
            </div>
            <div style="width:0;height:0;border-left:4px solid transparent;border-right:4px solid transparent;border-top:5px solid var(--sandstone);margin-top:-1px;"></div>
          </div>
        `,
        className: "location-picker-pin",
        iconSize: [28, 33],
        iconAnchor: [14, 32],
      });

      if (lat !== null && lon !== null) {
        const marker = L.marker([lat, lon], { icon: pinIcon }).addTo(map);
        markerRef.current = marker;
      }

      map.on("click", (e) => {
        const newLat = Number(e.latlng.lat.toFixed(4));
        const newLon = Number(e.latlng.lng.toFixed(4));
        onChange(newLat, newLon);

        if (markerRef.current) {
          markerRef.current.setLatLng([newLat, newLon]);
        } else {
          markerRef.current = L.marker([newLat, newLon], { icon: pinIcon }).addTo(map);
        }
      });

      mapRef.current = map;
    }

    void initMap();

    return () => {
      isMounted = false;
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
        markerRef.current = null;
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Synchronise external lat/lon changes into marker and map center
  useEffect(() => {
    if (!mapRef.current) return;
    if (lat !== null && lon !== null) {
      if (markerRef.current) {
        markerRef.current.setLatLng([lat, lon]);
      }
    }
  }, [lat, lon]);

  return (
    <div className="relative w-full h-56 rounded-[6px] overflow-hidden border border-sandstone">
      <div ref={containerRef} className="w-full h-full bg-stone" />
      <div className="absolute top-2 left-2 z-[400] bg-paper/90 px-2.5 py-1 rounded-[4px] border border-sandstone/70 type-caption text-ink font-medium shadow-sm">
        Click on the map to set location
      </div>
    </div>
  );
}
