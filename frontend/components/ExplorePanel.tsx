"use client";

import React from "react";
import type { SiteDetail, SiteSummary } from "@/lib/types";
import { ProvenanceChip } from "./ProvenanceChip";

export interface ExplorePanelProps {
  sites: SiteSummary[];
  selectedSite: SiteDetail | null;
  selectedSiteId: number | null;
  isLoadingSites: boolean;
  isLoadingDetail: boolean;
  error: string | null;
  searchQuery: string;
  selectedRegion: string;
  selectedCategory: string;
  verifiedOnly: boolean;
  onSearchChange: (query: string) => void;
  onRegionChange: (region: string) => void;
  onCategoryChange: (category: string) => void;
  onVerifiedOnlyChange: (verifiedOnly: boolean) => void;
  onSelectSite: (id: number) => void;
  onClearFilters: () => void;
  onClosePreview: () => void;
  onRetry: () => void;
}

/**
 * Category glyph icons for list rows per DESIGN.md
 */
function CategoryIcon({ category }: { category: string }) {
  const cat = category.toLowerCase();

  if (cat.includes("stepwell") || cat.includes("vav") || cat.includes("baori")) {
    return (
      <svg
        className="w-4 h-4 shrink-0 text-indigo"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M3 6h4v4h4v4h4v4h5" />
        <path d="M11 18h9" />
      </svg>
    );
  }

  if (cat.includes("fort")) {
    return (
      <svg
        className="w-4 h-4 shrink-0 text-indigo"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M4 21V7l3-3 3 3 4-4 4 4 3-3v17H4z" />
        <path d="M9 13h6v8H9v-8z" />
      </svg>
    );
  }

  if (cat.includes("temple")) {
    return (
      <svg
        className="w-4 h-4 shrink-0 text-indigo"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M12 2l-7 9h14l-7-9z" />
        <path d="M6 11v10h12V11" />
        <path d="M10 21v-5h4v5" />
      </svg>
    );
  }

  return (
    <svg
      className="w-4 h-4 shrink-0 text-indigo"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="5" y="4" width="14" height="16" rx="2" />
      <line x1="9" y1="9" x2="15" y2="9" />
      <line x1="9" y1="13" x2="15" y2="13" />
    </svg>
  );
}

export const ExplorePanel: React.FC<ExplorePanelProps> = ({
  sites,
  selectedSite,
  selectedSiteId,
  isLoadingSites,
  isLoadingDetail,
  error,
  searchQuery,
  selectedRegion,
  selectedCategory,
  verifiedOnly,
  onSearchChange,
  onRegionChange,
  onCategoryChange,
  onVerifiedOnlyChange,
  onSelectSite,
  onClearFilters,
  onClosePreview,
  onRetry,
}) => {
  return (
    <aside className="w-full h-full flex flex-col bg-paper border-r border-sandstone overflow-hidden">
      {/* If a site preview is active */}
      {selectedSiteId !== null ? (
        <div className="flex-1 flex flex-col overflow-y-auto p-4 sm:p-6 space-y-5">
          {/* Back button */}
          <button
            type="button"
            onClick={onClosePreview}
            className="self-start inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] border border-sandstone bg-stone/50 hover:bg-stone text-indigo type-small font-medium focus-ring transition-colors"
          >
            <span aria-hidden="true">&larr;</span>
            <span>All sites</span>
          </button>

          {isLoadingDetail || !selectedSite ? (
            <div className="space-y-4 animate-pulse pt-2">
              <div className="h-8 bg-stone rounded-[6px] w-3/4" />
              <div className="h-4 bg-stone rounded-[6px] w-1/3" />
              <div className="h-44 bg-stone rounded-none w-full" />
              <div className="h-20 bg-stone rounded-[6px] w-full" />
            </div>
          ) : (
            <div className="space-y-5">
              {/* Site header */}
              <div>
                <h2 className="type-h2 text-indigo">{selectedSite.name}</h2>
                <div className="flex items-center gap-2 mt-1.5 text-mute type-small">
                  <CategoryIcon category={selectedSite.category} />
                  <span className="capitalize">{selectedSite.category}</span>
                  <span>&bull;</span>
                  <span>{selectedSite.region}</span>
                </div>
              </div>

              {/* Photo section per DESIGN.md: large photo leading, radius 0, attribution under photo */}
              {selectedSite.images && selectedSite.images.length > 0 && (
                <div className="space-y-1.5">
                  <div className="relative w-full aspect-video bg-stone overflow-hidden rounded-none border border-sandstone">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={selectedSite.images[0].url}
                      alt={selectedSite.name}
                      className="w-full h-full object-cover rounded-none"
                    />
                  </div>
                  <div className="type-caption text-mute">
                    Photo by {selectedSite.images[0].author} &bull; Licence:{" "}
                    {selectedSite.images[0].licence}
                  </div>
                </div>
              )}

              {/* Field note under 3 px sandstone rule per DESIGN.md Section 3 */}
              <div className="field-note-rule space-y-1 bg-stone/20 py-2 pr-2">
                <span className="type-caption text-sandstone font-semibold block">
                  Field note
                </span>
                <p className="type-body text-ink">{selectedSite.description}</p>
              </div>

              {/* Provenance Tags */}
              {selectedSite.images &&
                selectedSite.images[0]?.tags &&
                selectedSite.images[0].tags.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-sandstone">
                    <span className="type-small font-semibold text-ink block">
                      Architectural features &amp; tags
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {selectedSite.images[0].tags.map((tag) => (
                        <ProvenanceChip
                          key={tag.id}
                          status={tag.status}
                          label={tag.label}
                          score={tag.score}
                        />
                      ))}
                    </div>
                  </div>
                )}
            </div>
          )}
        </div>
      ) : (
        /* Results list and filter panel */
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Filters header */}
          <div className="p-4 sm:p-5 border-b border-sandstone space-y-3.5 bg-paper shrink-0">
            {/* Search input */}
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                placeholder="Search sites or features..."
                aria-label="Search sites or architectural features"
                className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3.5 py-2 type-small text-ink placeholder:text-mute focus-ring transition-colors"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => onSearchChange("")}
                  aria-label="Clear search text"
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-mute hover:text-ink text-sm px-1"
                >
                  &times;
                </button>
              )}
            </div>

            {/* Region selector */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[13px]">
              <span className="text-mute font-medium mr-1 shrink-0">Region:</span>
              {[
                { label: "All", value: "" },
                { label: "Gujarat", value: "Gujarat" },
                { label: "Rajasthan", value: "Rajasthan" },
              ].map((r) => (
                <button
                  key={r.label}
                  type="button"
                  onClick={() => onRegionChange(r.value)}
                  className={`px-2.5 py-1 rounded-[6px] shrink-0 border transition-colors focus-ring ${
                    selectedRegion.toLowerCase() === r.value.toLowerCase()
                      ? "bg-indigo text-paper border-indigo font-semibold"
                      : "bg-paper text-ink border-sandstone hover:bg-stone"
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>

            {/* Category selector */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[13px]">
              <span className="text-mute font-medium mr-1 shrink-0">Type:</span>
              {[
                { label: "All", value: "" },
                { label: "Stepwell", value: "stepwell" },
                { label: "Fort", value: "fort" },
                { label: "Temple", value: "temple" },
              ].map((c) => (
                <button
                  key={c.label}
                  type="button"
                  onClick={() => onCategoryChange(c.value)}
                  className={`px-2.5 py-1 rounded-[6px] shrink-0 border transition-colors focus-ring ${
                    selectedCategory.toLowerCase() === c.value.toLowerCase()
                      ? "bg-indigo text-paper border-indigo font-semibold"
                      : "bg-paper text-ink border-sandstone hover:bg-stone"
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>

            {/* Verified only checkbox */}
            <div className="flex items-center justify-between pt-1">
              <label className="inline-flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={verifiedOnly}
                  onChange={(e) => onVerifiedOnlyChange(e.target.checked)}
                  className="rounded-[4px] border-sandstone text-indigo focus-ring"
                />
                <span className="type-caption text-ink font-medium">
                  Verified tags only
                </span>
              </label>

              {(searchQuery || selectedRegion || selectedCategory || verifiedOnly) && (
                <button
                  type="button"
                  onClick={onClearFilters}
                  className="type-caption text-mute hover:text-clay-red underline focus-ring"
                >
                  Clear filters
                </button>
              )}
            </div>
          </div>

          {/* Results count banner */}
          <div className="px-4 py-2 bg-stone/50 border-b border-sandstone flex items-center justify-between shrink-0">
            <span className="type-caption text-mute">
              {isLoadingSites ? (
                "Loading sites..."
              ) : (
                <>
                  <span className="font-semibold text-ink tabular-nums">
                    {sites.length}
                  </span>{" "}
                  {sites.length === 1 ? "site" : "sites"} documented
                </>
              )}
            </span>
          </div>

          {/* Site list area with Loading, Error, Empty, and Result rows */}
          <div className="flex-1 overflow-y-auto divide-y divide-sandstone/60">
            {/* Loading state skeleton */}
            {isLoadingSites && (
              <div className="p-4 space-y-3">
                {[1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className="p-3 bg-stone/40 rounded-[6px] border border-sandstone/40 animate-pulse space-y-2"
                  >
                    <div className="h-5 bg-stone rounded w-3/5" />
                    <div className="h-3 bg-stone rounded w-2/5" />
                  </div>
                ))}
              </div>
            )}

            {/* Error state per DESIGN.md Section 11 */}
            {!isLoadingSites && error && (
              <div className="p-6 text-center space-y-3">
                <div className="text-clay-red type-small font-semibold">
                  {error}
                </div>
                <p className="type-caption text-mute">
                  Check your network connection or backend server status.
                </p>
                <button
                  type="button"
                  onClick={onRetry}
                  className="px-4 py-1.5 bg-paper border border-sandstone rounded-[6px] text-indigo type-small font-semibold focus-ring hover:bg-stone"
                >
                  Retry
                </button>
              </div>
            )}

            {/* Empty state per DESIGN.md Section 11 */}
            {!isLoadingSites && !error && sites.length === 0 && (
              <div className="p-6 text-center space-y-4">
                <p className="type-body text-ink">
                  No sites match these filters. Clear a filter or upload a photo of a site.
                </p>
                <button
                  type="button"
                  onClick={onClearFilters}
                  className="px-4 py-2 bg-indigo text-paper rounded-[6px] type-small font-semibold focus-ring hover:bg-indigo/90"
                >
                  Clear filters
                </button>
              </div>
            )}

            {/* Result rows */}
            {!isLoadingSites &&
              !error &&
              sites.map((site) => {
                const isSelected = site.id === selectedSiteId;
                return (
                  <button
                    key={site.id}
                    type="button"
                    onClick={() => onSelectSite(site.id)}
                    className={`w-full text-left p-4 transition-colors flex items-start gap-3 focus-ring ${
                      isSelected
                        ? "bg-stone border-l-4 border-indigo font-semibold"
                        : "hover:bg-stone/50 bg-paper"
                    }`}
                  >
                    <div className="mt-1">
                      <CategoryIcon category={site.category} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-serif font-semibold text-ink text-[17px] leading-[22px] truncate">
                        {site.name}
                      </div>
                      <div className="type-caption text-mute mt-0.5 capitalize">
                        {site.category} &bull; {site.region}
                      </div>
                    </div>
                    <span
                      aria-hidden="true"
                      className="text-sandstone text-sm self-center"
                    >
                      &rsaquo;
                    </span>
                  </button>
                );
              })}
          </div>
        </div>
      )}
    </aside>
  );
};
