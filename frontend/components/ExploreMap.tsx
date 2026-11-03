"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Map as LeafletMap, MarkerClusterGroup } from "leaflet";
import type { SiteSummary } from "@/lib/types";

export interface ExploreMapProps {
  sites: SiteSummary[];
  selectedSiteId: number | null;
  onSelectSite: (id: number) => void;
  flyToSite?: SiteSummary | null;
}

interface WindowWithLeaflet extends Window {
  L?: unknown;
}

interface ClusterWithCount {
  getChildCount: () => number;
}

/**
 * SVG category glyphs per DESIGN.md:
 * Glyph differs by site category (stepwell, fort, temple, monument)
 */
function getCategoryGlyphSvg(category: string, isSelected: boolean): string {
  const color = isSelected ? "#F7F8F5" : "#1A1D26";
  const cat = category.toLowerCase();

  if (cat.includes("stepwell") || cat.includes("vav") || cat.includes("baori")) {
    return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M3 6h4v4h4v4h4v4h5" />
      <path d="M11 18h9" />
    </svg>`;
  }

  if (cat.includes("fort")) {
    return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M4 21V7l3-3 3 3 4-4 4 4 3-3v17H4z" />
      <path d="M9 13h6v8H9v-8z" />
    </svg>`;
  }

  if (cat.includes("temple")) {
    return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M12 2l-7 9h14l-7-9z" />
      <path d="M6 11v10h12V11" />
      <path d="M10 21v-5h4v5" />
    </svg>`;
  }

  // Default heritage stone structure
  return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <rect x="5" y="4" width="14" height="16" rx="2" />
    <line x1="9" y1="9" x2="15" y2="9" />
    <line x1="9" y1="13" x2="15" y2="13" />
  </svg>`;
}

function createPinHtml(category: string, isSelected: boolean, name: string): string {
  const bg = isSelected ? "var(--indigo)" : "var(--paper)";
  const border = isSelected ? "2px solid var(--sandstone)" : "1.5px solid var(--sandstone)";
  const shadow = isSelected
    ? "0 4px 12px rgba(37, 48, 94, 0.45)"
    : "0 2px 6px rgba(26, 29, 38, 0.18)";
  const scale = isSelected ? "transform: scale(1.15);" : "";
  const glyph = getCategoryGlyphSvg(category, isSelected);

  return `
    <div style="display:flex;flex-direction:column;align-items:center;cursor:pointer;${scale}transition:transform 0.15s ease;" title="${name}" role="button" aria-label="${name}">
      <div style="width:34px;height:34px;border-radius:9999px;background:${bg};border:${border};box-shadow:${shadow};display:flex;align-items:center;justify-content:center;">
        ${glyph}
      </div>
      <div style="width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;border-top:6px solid var(--sandstone);margin-top:-1px;"></div>
    </div>
  `;
}

export default function ExploreMap({
  sites,
  selectedSiteId,
  onSelectSite,
  flyToSite,
}: ExploreMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<LeafletMap | null>(null);
  const clusterGroupRef = useRef<MarkerClusterGroup | null>(null);
  const fitSitesRef = useRef<(() => void) | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState(false);

  const validSites = useMemo(
    () =>
      sites.filter(
        (site) =>
          Number.isFinite(site.lat) &&
          Number.isFinite(site.lon) &&
          site.lat >= -90 &&
          site.lat <= 90 &&
          site.lon >= -180 &&
          site.lon <= 180
      ),
    [sites]
  );

  // Initialise map
  useEffect(() => {
    let isMounted = true;

    async function initLeaflet() {
      if (!mapContainerRef.current || mapInstanceRef.current) return;

      const leafletModule = await import("leaflet");
      // MarkerCluster augments Leaflet at runtime. Use the mutable default
      // export rather than Turbopack's frozen module namespace.
      const L = leafletModule.default ?? leafletModule;
      // MarkerCluster attaches to window.L
      (window as WindowWithLeaflet).L = L;
      await import("leaflet.markercluster");

      if (!isMounted || !mapContainerRef.current) return;

      // Center over Gujarat and Rajasthan heritage region
      const map = L.map(mapContainerRef.current, {
        center: [24.8, 73.8],
        zoom: 7,
        zoomControl: false,
      });

      const tileLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
      });
      tileLayer.on("tileerror", () => {
        setMapError("Map tiles could not be loaded. Check your network connection.");
      });
      tileLayer.on("tileload", () => setMapError(null));
      tileLayer.addTo(map);

      // Custom positioned zoom control in bottom-right
      L.control.zoom({ position: "bottomright" }).addTo(map);

      // Custom marker cluster group styled with DESIGN.md tokens
      const clusterGroup = L.markerClusterGroup({
        showCoverageOnHover: false,
        maxClusterRadius: 45,
        iconCreateFunction: (cluster: ClusterWithCount) => {
          const count = cluster.getChildCount();
          return L.divIcon({
            html: `<div class="heritage-cluster w-8 h-8">${count}</div>`,
            className: "custom-cluster-wrapper",
            iconSize: [32, 32],
            iconAnchor: [16, 16],
          });
        },
      });

      map.addLayer(clusterGroup);

      mapInstanceRef.current = map;
      clusterGroupRef.current = clusterGroup;
      setMapReady(true);
      const resizeObserver = new ResizeObserver(() => map.invalidateSize());
      resizeObserver.observe(mapContainerRef.current);
      window.setTimeout(() => map.invalidateSize(), 0);

      return () => resizeObserver.disconnect();
    }

    let cleanup: (() => void) | undefined;
    void initLeaflet().then((value) => {
      cleanup = value;
    });

    return () => {
      isMounted = false;
      cleanup?.();
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        clusterGroupRef.current = null;
        setMapReady(false);
      }
    };
  }, []);

  // Update markers when sites or selectedSiteId change
  useEffect(() => {
    let isMounted = true;

    async function updateMarkers() {
      if (!mapInstanceRef.current || !clusterGroupRef.current) return;
      const leafletModule = await import("leaflet");
      const L = leafletModule.default ?? leafletModule;
      if (!isMounted) return;

      const clusterGroup = clusterGroupRef.current;
      clusterGroup.clearLayers();

      validSites.forEach((site) => {
        const isSelected = site.id === selectedSiteId;
        const pinIcon = L.divIcon({
          html: createPinHtml(site.category, isSelected, site.name),
          className: "custom-site-pin",
          iconSize: [34, 40],
          iconAnchor: [17, 39],
        });

        const marker = L.marker([site.lat, site.lon], { icon: pinIcon });
        marker.on("click", () => {
          onSelectSite(site.id);
        });

        clusterGroup.addLayer(marker);
      });
    }

    void updateMarkers();

    return () => {
      isMounted = false;
    };
  }, [mapReady, validSites, selectedSiteId, onSelectSite]);

  const fitAllSites = useCallback(() => {
    const map = mapInstanceRef.current;
    if (!map || validSites.length === 0) return;
    const bounds = validSites.map((site) => [site.lat, site.lon] as [number, number]);
    map.fitBounds(bounds, { padding: [36, 36], maxZoom: 10, animate: true });
  }, [validSites]);

  useEffect(() => {
    fitSitesRef.current = fitAllSites;
  }, [fitAllSites]);

  useEffect(() => {
    if (!mapReady || !mapInstanceRef.current || validSites.length === 0) return;
    const timer = window.setTimeout(() => {
      mapInstanceRef.current?.invalidateSize();
      fitAllSites();
    }, 100);
    return () => window.clearTimeout(timer);
  }, [fitAllSites, mapReady, validSites.length]);

  // Single fly-to motion respecting prefers-reduced-motion
  useEffect(() => {
    if (!mapInstanceRef.current || !flyToSite) return;

    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    mapInstanceRef.current.flyTo([flyToSite.lat, flyToSite.lon], 13, {
      animate: !prefersReducedMotion,
      duration: prefersReducedMotion ? 0 : 0.8,
    });
  }, [flyToSite]);

  return (
    <div className="relative w-full h-full min-h-[420px] overflow-hidden bg-stone">
      <div
        ref={mapContainerRef}
        className="w-full h-full min-h-[420px] z-0 bg-stone"
        style={{ height: "100%", minHeight: "420px" }}
        aria-label="Interactive map of heritage sites"
      />
      <div className="absolute left-4 top-4 z-[400] flex flex-col gap-2">
        <button
          type="button"
          onClick={() => fitSitesRef.current?.()}
          disabled={validSites.length === 0}
          className="rounded-full border border-sandstone bg-paper px-4 py-2 text-sm font-semibold text-indigo shadow-lg transition hover:bg-stone disabled:cursor-not-allowed disabled:opacity-50"
        >
          Fit all sites
        </button>
        {mapError && (
          <div
            role="alert"
            className="max-w-[260px] rounded-lg border border-terracotta/40 bg-paper px-3 py-2 text-xs leading-5 text-ink shadow-lg"
          >
            {mapError}
          </div>
        )}
      </div>
      {validSites.length === 0 && (
        <div className="absolute inset-0 z-[400] flex items-center justify-center bg-paper/90 p-6 text-center">
          <p className="max-w-xs text-sm text-ink">
            No sites with valid coordinates match the current filters.
          </p>
        </div>
      )}
    </div>
  );
}
