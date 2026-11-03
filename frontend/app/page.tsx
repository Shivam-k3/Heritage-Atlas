"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { Navbar } from "@/components/Navbar";
import { ExplorePanel } from "@/components/ExplorePanel";
import { MobileBottomSheet } from "@/components/MobileBottomSheet";
import { CinematicHome } from "@/components/CinematicHome";
import { getSiteById, getSites } from "@/lib/api";
import type { SiteDetail, SiteSummary } from "@/lib/types";

// Dynamic client import for Leaflet map with SSR disabled
const ExploreMap = dynamic(() => import("@/components/ExploreMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-stone flex items-center justify-center text-mute type-small">
      <div className="flex flex-col items-center gap-2">
        <div className="w-6 h-6 border-2 border-sandstone border-t-indigo rounded-full animate-spin" />
        <span>Loading map tiles...</span>
      </div>
    </div>
  ),
});

export default function ExplorePage() {
  const [allSites, setAllSites] = useState<SiteSummary[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<number | null>(null);
  const [selectedSiteDetail, setSelectedSiteDetail] = useState<SiteDetail | null>(null);
  const [flyToSite, setFlyToSite] = useState<SiteSummary | null>(null);

  const [isLoadingSites, setIsLoadingSites] = useState<boolean>(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedRegion, setSelectedRegion] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [verifiedOnly, setVerifiedOnly] = useState<boolean>(false);
  const [reloadTrigger, setReloadTrigger] = useState<number>(0);

  // Fetch sites asynchronously adhering to React 19 effect rules
  useEffect(() => {
    let ignore = false;

    getSites({
      region: selectedRegion || undefined,
    })
      .then((data) => {
        if (!ignore) {
          setAllSites(data);
          setError(null);
          setIsLoadingSites(false);
        }
      })
      .catch((err: unknown) => {
        if (!ignore) {
          setError(
            err instanceof Error
              ? err.message
              : "Couldn't load sites. Check your connection or try refreshing the page."
          );
          setIsLoadingSites(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [selectedRegion, reloadTrigger]);

  const handleRetry = useCallback(() => {
    setIsLoadingSites(true);
    setReloadTrigger((prev) => prev + 1);
  }, []);

  const handleRegionChange = useCallback((region: string) => {
    setIsLoadingSites(true);
    setSelectedRegion(region);
  }, []);

  const handleCategoryChange = useCallback((category: string) => {
    setSelectedCategory(category);
  }, []);

  const handleVerifiedOnlyChange = useCallback((verified: boolean) => {
    setVerifiedOnly(verified);
  }, []);

  // Client-side filtering per Task 5: region uses API; category and search query work client-side
  const displayedSites = useMemo(() => {
    let result = allSites;
    if (selectedCategory) {
      const cat = selectedCategory.toLowerCase();
      result = result.filter((s) => s.category.toLowerCase() === cat);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.category.toLowerCase().includes(q) ||
          s.region.toLowerCase().includes(q)
      );
    }
    return result;
  }, [allSites, selectedCategory, searchQuery]);

  // Handle site selection (from list or map pin click)
  const handleSelectSite = useCallback(
    async (siteId: number) => {
      setSelectedSiteId(siteId);

      // Locate summary to trigger single fly-to
      const targetSite = allSites.find((s) => s.id === siteId);
      if (targetSite) {
        setFlyToSite(targetSite);
      }

      // Fetch site details for preview
      setIsLoadingDetail(true);
      try {
        const detail = await getSiteById(siteId);
        setSelectedSiteDetail(detail);
      } catch (err: unknown) {
        console.error("Failed to fetch site detail:", err);
      } finally {
        setIsLoadingDetail(false);
      }
    },
    [allSites]
  );

  const handleClosePreview = useCallback(() => {
    setSelectedSiteId(null);
    setSelectedSiteDetail(null);
    setFlyToSite(null);
  }, []);

  const handleClearFilters = useCallback(() => {
    setIsLoadingSites(true);
    setSearchQuery("");
    setSelectedRegion("");
    setSelectedCategory("");
    setVerifiedOnly(false);
  }, []);

  return (
    <div className="min-h-screen bg-stone flex flex-col">
      <Navbar />
      <CinematicHome />

      <main id="explore-map" className="cinema-map-section flex-none relative flex flex-col md:flex-row h-[760px] md:h-[760px] min-h-0 overflow-hidden">
        {/* Desktop 400 px left panel */}
        <div className="hidden md:block w-[400px] shrink-0 h-full">
          <ExplorePanel
            sites={displayedSites}
            selectedSite={selectedSiteDetail}
            selectedSiteId={selectedSiteId}
            isLoadingSites={isLoadingSites}
            isLoadingDetail={isLoadingDetail}
            error={error}
            searchQuery={searchQuery}
            selectedRegion={selectedRegion}
            selectedCategory={selectedCategory}
            verifiedOnly={verifiedOnly}
            onSearchChange={setSearchQuery}
            onRegionChange={handleRegionChange}
            onCategoryChange={handleCategoryChange}
            onVerifiedOnlyChange={handleVerifiedOnlyChange}
            onSelectSite={handleSelectSite}
            onClearFilters={handleClearFilters}
            onClosePreview={handleClosePreview}
            onRetry={handleRetry}
          />
        </div>

        {/* Map area (full height on desktop and mobile) */}
        <section
          aria-label="Heritage map"
          className="flex-1 h-[calc(100vh-56px)] min-h-[420px] md:h-[calc(100vh-56px)] w-full relative"
        >
          <ExploreMap
            sites={displayedSites}
            selectedSiteId={selectedSiteId}
            onSelectSite={handleSelectSite}
            flyToSite={flyToSite}
          />
        </section>

        {/* Mobile bottom sheet on 375 px viewport per DESIGN.md */}
        <MobileBottomSheet
          siteCount={displayedSites.length}
          selectedSiteName={selectedSiteDetail?.name}
        >
          <ExplorePanel
            sites={displayedSites}
            selectedSite={selectedSiteDetail}
            selectedSiteId={selectedSiteId}
            isLoadingSites={isLoadingSites}
            isLoadingDetail={isLoadingDetail}
            error={error}
            searchQuery={searchQuery}
            selectedRegion={selectedRegion}
            selectedCategory={selectedCategory}
            verifiedOnly={verifiedOnly}
            onSearchChange={setSearchQuery}
            onRegionChange={handleRegionChange}
            onCategoryChange={handleCategoryChange}
            onVerifiedOnlyChange={handleVerifiedOnlyChange}
            onSelectSite={handleSelectSite}
            onClearFilters={handleClearFilters}
            onClosePreview={handleClosePreview}
            onRetry={handleRetry}
          />
        </MobileBottomSheet>
      </main>
    </div>
  );
}
