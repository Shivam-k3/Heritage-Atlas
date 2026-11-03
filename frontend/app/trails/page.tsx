"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import {
  addTrailStop,
  createTrail,
  createTrailFromImages,
  getSites,
  getTrail,
  getTrailJournal,
  getTrailSummary,
  getTrails,
  moveStopIds,
  removeTrailStop,
  reorderTrailStops,
} from "@/lib/api";
import type {
  SiteSummary,
  Trail,
  TrailJournal,
  TrailSummary,
} from "@/lib/types";

const TrailMap = dynamic(() => import("@/components/TrailMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-72 sm:h-96 bg-stone border border-sandstone rounded-[6px] flex items-center justify-center text-mute type-caption">
      Loading trail map...
    </div>
  ),
});

function formatVisitDate(value?: string | null): string {
  if (!value) return "Visit date not recorded";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatCreatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export default function TrailsPage() {
  const [trails, setTrails] = useState<Trail[]>([]);
  const [isLoadingTrails, setIsLoadingTrails] = useState<boolean>(true);
  const [trailsError, setTrailsError] = useState<string | null>(null);
  const [trailsVersion, setTrailsVersion] = useState<number>(0);
  const [selectedTrailId, setSelectedTrailId] = useState<number | null>(null);

  const [trail, setTrail] = useState<Trail | null>(null);
  const [summary, setSummary] = useState<TrailSummary | null>(null);
  const [journal, setJournal] = useState<TrailJournal | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [journalError, setJournalError] = useState<string | null>(null);
  const [detailVersion, setDetailVersion] = useState<number>(0);

  const [sites, setSites] = useState<SiteSummary[]>([]);
  const [isLoadingSites, setIsLoadingSites] = useState<boolean>(true);
  const [sitesError, setSitesError] = useState<string | null>(null);

  // Create form
  const [title, setTitle] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [createdBy, setCreatedBy] = useState<string>("");
  const [isPublic, setIsPublic] = useState<boolean>(false);
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createMessage, setCreateMessage] = useState<string | null>(null);

  // Add stop form. Site detail "Add to trail" arrives as /trails?site=<id>.
  const [stopSiteId, setStopSiteId] = useState<string>(() => {
    if (typeof window === "undefined") return "";
    return new URLSearchParams(window.location.search).get("site") ?? "";
  });
  const [stopVisitDate, setStopVisitDate] = useState<string>("");
  const [stopNote, setStopNote] = useState<string>("");
  const [isAddingStop, setIsAddingStop] = useState<boolean>(false);
  const [stopError, setStopError] = useState<string | null>(null);
  const [stopMessage, setStopMessage] = useState<string | null>(null);

  // Reorder / remove
  const [isMutating, setIsMutating] = useState<boolean>(false);
  const [mutationError, setMutationError] = useState<string | null>(null);

  // Load trails
  useEffect(() => {
    let ignore = false;

    async function loadTrails() {
      setIsLoadingTrails(true);
      setTrailsError(null);
      try {
        const data = await getTrails({ limit: 100 });
        if (ignore) return;
        setTrails(data);
        setSelectedTrailId((current) => {
          if (current && data.some((item) => item.id === current)) return current;
          return data[0]?.id ?? null;
        });
      } catch (err: unknown) {
        if (!ignore) {
          setTrailsError(
            errorMessage(
              err,
              "Could not load trails. Check that the backend is running."
            )
          );
        }
      } finally {
        if (!ignore) setIsLoadingTrails(false);
      }
    }

    void loadTrails();
    return () => {
      ignore = true;
    };
  }, [trailsVersion]);

  // Load sites for the add-stop picker
  useEffect(() => {
    let ignore = false;

    async function loadSites() {
      setIsLoadingSites(true);
      setSitesError(null);
      try {
        const data = await getSites();
        if (!ignore) setSites(data);
      } catch (err: unknown) {
        if (!ignore) {
          setSitesError(
            errorMessage(err, "Could not load the site list for adding stops.")
          );
        }
      } finally {
        if (!ignore) setIsLoadingSites(false);
      }
    }

    void loadSites();
    return () => {
      ignore = true;
    };
  }, []);

  // Load selected trail, its summary and its generated journal
  useEffect(() => {
    if (selectedTrailId === null) return;

    let ignore = false;

    async function loadDetail() {
      setIsLoadingDetail(true);
      setDetailError(null);
      setSummaryError(null);
      setJournalError(null);
      setTrail(null);
      setSummary(null);
      setJournal(null);

      try {
        const detail = await getTrail(selectedTrailId as number);
        if (ignore) return;
        setTrail(detail);
      } catch (err: unknown) {
        if (!ignore) {
          setDetailError(
            errorMessage(err, "Could not load this trail from the server.")
          );
          setIsLoadingDetail(false);
        }
        return;
      }

      if (ignore) return;
      setIsLoadingDetail(false);

      const [summaryResult, journalResult] = await Promise.allSettled([
        getTrailSummary(selectedTrailId as number),
        getTrailJournal(selectedTrailId as number),
      ]);

      if (ignore) return;
      if (summaryResult.status === "fulfilled") {
        setSummary(summaryResult.value);
      } else {
        setSummaryError(
          errorMessage(
            summaryResult.reason,
            "Route summary is unavailable for this trail."
          )
        );
      }
      if (journalResult.status === "fulfilled") {
        setJournal(journalResult.value);
      } else {
        setJournalError(
          errorMessage(
            journalResult.reason,
            "Generated journal is unavailable for this trail."
          )
        );
      }
    }

    void loadDetail();
    return () => {
      ignore = true;
    };
  }, [selectedTrailId, detailVersion]);

  const refreshTrail = useCallback(() => {
    setDetailVersion((value) => value + 1);
    setTrailsVersion((value) => value + 1);
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreateError(null);
    setCreateMessage(null);
    if (!title.trim()) {
      setCreateError("Give the trail a title.");
      return;
    }

    setIsCreating(true);
    try {
      const created = await createTrail({
        title: title.trim(),
        description: description.trim() || null,
        created_by: createdBy.trim() || null,
        is_public: isPublic,
      });
      setTrails((current) => [created, ...current]);
      setSelectedTrailId(created.id);
      setTitle("");
      setDescription("");
      setCreateMessage(`Trail "${created.title}" created. Add stops below.`);
    } catch (err: unknown) {
      setCreateError(errorMessage(err, "Could not create the trail."));
    } finally {
      setIsCreating(false);
    }
  }

  async function handleCreateFromImages() {
    setCreateError(null);
    setCreateMessage(null);
    if (!title.trim()) {
      setCreateError("Give the trail a title before building it from photos.");
      return;
    }

    setIsCreating(true);
    try {
      const result = await createTrailFromImages({
        title: title.trim(),
        description: description.trim() || null,
        created_by: createdBy.trim() || null,
        is_public: isPublic,
      });
      setTrails((current) => [result.trail, ...current]);
      setSelectedTrailId(result.trail.id);
      setTitle("");
      setDescription("");
      setCreateMessage(
        `Built "${result.trail.title}" from ${result.images_used} photo(s). ` +
          `${result.images_skipped} photo(s) skipped because they had no capture time or site coordinates.`
      );
    } catch (err: unknown) {
      setCreateError(
        errorMessage(
          err,
          "Could not build a trail from photos. No trail was created."
        )
      );
    } finally {
      setIsCreating(false);
    }
  }

  async function handleAddStop(e: React.FormEvent) {
    e.preventDefault();
    setStopError(null);
    setStopMessage(null);
    if (!trail) {
      setStopError("Create or select a trail first.");
      return;
    }
    if (!stopSiteId) {
      setStopError("Pick a heritage site for this stop.");
      return;
    }

    setIsAddingStop(true);
    try {
      const stop = await addTrailStop(trail.id, {
        site_id: Number(stopSiteId),
        visit_date: stopVisitDate || null,
        note: stopNote.trim() || null,
      });
      setStopMessage(`${stop.site_name} added as stop ${stop.stop_order}.`);
      setStopVisitDate("");
      setStopNote("");
      refreshTrail();
    } catch (err: unknown) {
      setStopError(errorMessage(err, "Could not add the stop."));
    } finally {
      setIsAddingStop(false);
    }
  }

  async function handleMove(stopId: number, direction: -1 | 1) {
    if (!trail || isMutating) return;
    const ids = trail.stops.map((stop) => stop.id);
    const next = moveStopIds(ids, stopId, direction);
    if (next.every((id, index) => id === ids[index])) return;

    setIsMutating(true);
    setMutationError(null);
    try {
      const stops = await reorderTrailStops(trail.id, next);
      setTrail({ ...trail, stops });
      refreshTrail();
    } catch (err: unknown) {
      setMutationError(errorMessage(err, "Could not reorder the stops."));
    } finally {
      setIsMutating(false);
    }
  }

  async function handleRemoveStop(stopId: number, siteName: string) {
    if (!trail || isMutating) return;
    if (!window.confirm(`Remove ${siteName} from this trail?`)) return;

    setIsMutating(true);
    setMutationError(null);
    try {
      const stops = await removeTrailStop(trail.id, stopId);
      setTrail({ ...trail, stops });
      refreshTrail();
    } catch (err: unknown) {
      setMutationError(errorMessage(err, "Could not remove the stop."));
    } finally {
      setIsMutating(false);
    }
  }

  const stopName = useCallback(
    (siteId: number): string =>
      trail?.stops.find((stop) => stop.site_id === siteId)?.site_name ??
      `Site #${siteId}`,
    [trail]
  );

  const missingNames = useMemo(() => {
    if (!summary) return [];
    return summary.missing_coordinates.map((siteId) => stopName(siteId));
  }, [summary, stopName]);

  return (
    <div className="min-h-screen bg-stone flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8 sm:px-6 md:py-10 space-y-8">
        <div>
          <h1 className="type-h1 text-indigo font-serif font-semibold">
            Explorer trails
          </h1>
          <p className="type-body text-mute mt-1">
            Build ordered journeys from documented sites. Distances are
            straight-line great-circle distances, never road distances.
          </p>
        </div>

        {/* Create trail */}
        <section className="bg-paper p-5 sm:p-6 rounded-[10px] border border-sandstone space-y-4">
          <h2 className="type-h2 text-indigo border-b border-sandstone pb-3">
            Create a trail
          </h2>

          {createError && (
            <div className="bg-clay-red/10 border border-clay-red text-clay-red p-3 rounded-[6px] type-small font-semibold">
              {createError}
            </div>
          )}
          {createMessage && (
            <div className="bg-water/10 border border-water text-water p-3 rounded-[6px] type-small font-medium">
              {createMessage}
            </div>
          )}

          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1 md:col-span-2">
                <label
                  htmlFor="trail-title"
                  className="type-caption font-semibold text-ink block"
                >
                  Trail title (required)
                </label>
                <input
                  id="trail-title"
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="E.g. Stepwells of Gujarat"
                  className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3.5 py-2.5 type-body text-ink placeholder:text-mute focus-ring"
                  maxLength={200}
                />
              </div>

              <div className="space-y-1">
                <label
                  htmlFor="trail-created-by"
                  className="type-caption font-semibold text-ink block"
                >
                  Created by (optional)
                </label>
                <input
                  id="trail-created-by"
                  type="text"
                  value={createdBy}
                  onChange={(e) => setCreatedBy(e.target.value)}
                  placeholder="Your name"
                  className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3.5 py-2.5 type-small text-ink placeholder:text-mute focus-ring"
                  maxLength={200}
                />
              </div>

              <label className="flex items-center gap-2 pt-6 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={isPublic}
                  onChange={(e) => setIsPublic(e.target.checked)}
                  className="rounded-[4px] border-sandstone text-indigo focus-ring"
                />
                <span className="type-small text-ink">Public trail</span>
              </label>

              <div className="space-y-1 md:col-span-2">
                <label
                  htmlFor="trail-description"
                  className="type-caption font-semibold text-ink block"
                >
                  Description (optional)
                </label>
                <textarea
                  id="trail-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  placeholder="What connects these sites?"
                  className="w-full bg-stone/30 border border-sandstone rounded-[6px] p-3 type-small text-ink placeholder:text-mute focus-ring"
                />
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 pt-1">
              <button
                type="submit"
                disabled={isCreating || !title.trim()}
                className="px-6 py-2.5 bg-indigo text-paper rounded-[6px] type-small font-semibold focus-ring hover:bg-indigo/90 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isCreating ? "Saving..." : "Create trail"}
              </button>
              <button
                type="button"
                onClick={() => void handleCreateFromImages()}
                disabled={isCreating || !title.trim()}
                className="px-6 py-2.5 bg-paper text-indigo border border-indigo/40 rounded-[6px] type-small font-semibold focus-ring hover:bg-indigo/5 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Build from photo EXIF
              </button>
            </div>
            <p className="type-caption text-mute">
              Photo EXIF trails only use photos with a capture time and site
              coordinates. Skipped photos are counted, never guessed.
            </p>
          </form>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6 items-start">
          {/* Trail list */}
          <aside className="bg-paper rounded-[10px] border border-sandstone p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-sandstone pb-2">
              <h2 className="type-h3 text-indigo">All trails</h2>
              <span className="type-caption text-mute tabular-nums">
                {trails.length}
              </span>
            </div>

            {isLoadingTrails && (
              <div className="space-y-2 animate-pulse">
                <div className="h-12 bg-stone/60 rounded-[6px]" />
                <div className="h-12 bg-stone/60 rounded-[6px]" />
              </div>
            )}

            {!isLoadingTrails && trailsError && (
              <div className="space-y-2">
                <p className="type-small text-clay-red font-semibold">
                  {trailsError}
                </p>
                <button
                  type="button"
                  onClick={() => setTrailsVersion((value) => value + 1)}
                  className="px-3 py-1.5 bg-stone text-ink border border-sandstone rounded-[6px] type-caption font-semibold focus-ring"
                >
                  Retry
                </button>
              </div>
            )}

            {!isLoadingTrails && !trailsError && trails.length === 0 && (
              <p className="type-small text-mute">
                No trails yet. Create one above.
              </p>
            )}

            {!isLoadingTrails && !trailsError && trails.length > 0 && (
              <ul className="space-y-2">
                {trails.map((item) => {
                  const selected = item.id === selectedTrailId;
                  return (
                    <li key={item.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedTrailId(item.id)}
                        aria-current={selected ? "true" : undefined}
                        className={`w-full text-left px-3 py-2.5 rounded-[6px] border transition-colors focus-ring ${
                          selected
                            ? "bg-indigo text-paper border-indigo"
                            : "bg-stone/30 text-ink border-sandstone hover:bg-stone"
                        }`}
                      >
                        <span className="type-small font-semibold block break-words">
                          {item.title}
                        </span>
                        <span
                          className={`type-caption block ${
                            selected ? "text-paper/80" : "text-mute"
                          }`}
                        >
                          {item.stops.length}{" "}
                          {item.stops.length === 1 ? "stop" : "stops"}
                          {item.is_public ? " · public" : ""}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </aside>

          {/* Selected trail detail */}
          <section className="space-y-6 min-w-0">
            {selectedTrailId === null && (
              <div className="bg-paper p-8 rounded-[10px] border border-sandstone text-center space-y-3">
                <h2 className="type-h2 text-indigo">No trail selected</h2>
                <p className="type-body text-mute">
                  Create a trail or pick one from the list to see its ordered
                  stops, route and journal.
                </p>
              </div>
            )}

            {isLoadingDetail && (
              <div className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-4 animate-pulse">
                <div className="h-7 bg-stone/60 rounded-[6px] w-1/2" />
                <div className="h-4 bg-stone/60 rounded-[6px] w-1/3" />
                <div className="h-72 bg-stone/60 rounded-[6px]" />
              </div>
            )}

            {!isLoadingDetail && detailError && (
              <div className="bg-paper p-6 rounded-[10px] border border-clay-red/40 space-y-3">
                <h2 className="type-h2 text-clay-red">Trail unavailable</h2>
                <p className="type-body text-ink">{detailError}</p>
                <button
                  type="button"
                  onClick={refreshTrail}
                  className="px-4 py-2 bg-indigo text-paper rounded-[6px] type-small font-semibold focus-ring"
                >
                  Retry
                </button>
              </div>
            )}

            {!isLoadingDetail && !detailError && trail && (
              <>
                <div className="bg-paper p-5 sm:p-6 rounded-[10px] border border-sandstone space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
                    <div className="min-w-0">
                      <h2 className="type-h2 text-indigo break-words">
                        {trail.title}
                      </h2>
                      <p className="type-caption text-mute mt-1">
                        {trail.stops.length}{" "}
                        {trail.stops.length === 1 ? "stop" : "stops"}
                        {trail.created_by ? ` · by ${trail.created_by}` : ""}
                        {trail.is_public ? " · public" : " · private"}
                        {` · created ${formatCreatedAt(trail.created_at)}`}
                      </p>
                    </div>
                    <span className="type-caption text-mute shrink-0">
                      Trail #{trail.id}
                    </span>
                  </div>
                  {trail.description && (
                    <p className="type-body text-ink">{trail.description}</p>
                  )}
                </div>

                {/* Map */}
                <div className="bg-paper p-4 sm:p-5 rounded-[10px] border border-sandstone space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="type-h3 text-indigo">Ordered route</h3>
                    <span className="type-caption text-mute">
                      Dashed lines are straight-line connections, not roads.
                    </span>
                  </div>
                  <TrailMap stops={trail.stops} />
                  {summary && missingNames.length > 0 && (
                    <p className="type-caption text-turmeric">
                      Missing coordinates, so those legs are omitted:{" "}
                      {missingNames.join(", ")}.
                    </p>
                  )}
                </div>

                {/* Summary */}
                <div className="bg-paper p-5 rounded-[10px] border border-sandstone space-y-4">
                  <h3 className="type-h3 text-indigo border-b border-sandstone pb-2">
                    Route summary
                  </h3>

                  {summaryError && (
                    <p className="type-small text-clay-red font-semibold">
                      {summaryError}
                    </p>
                  )}

                  {!summaryError && !summary && (
                    <p className="type-small text-mute">
                      Summary is loading...
                    </p>
                  )}

                  {!summaryError && summary && (
                    <>
                      <div className="grid grid-cols-3 gap-3 text-center">
                        <div className="bg-stone/40 border border-sandstone rounded-[6px] p-3">
                          <div className="type-caption text-mute">Sites</div>
                          <div className="type-h3 text-ink tabular-nums">
                            {summary.sites}
                          </div>
                        </div>
                        <div className="bg-stone/40 border border-sandstone rounded-[6px] p-3">
                          <div className="type-caption text-mute">Photos</div>
                          <div className="type-h3 text-ink tabular-nums">
                            {summary.photos}
                          </div>
                        </div>
                        <div className="bg-stone/40 border border-sandstone rounded-[6px] p-3">
                          <div className="type-caption text-mute">
                            Straight-line
                          </div>
                          <div className="type-h3 text-ink tabular-nums">
                            {summary.total_km.toFixed(1)} km
                          </div>
                        </div>
                      </div>

                      <p className="type-caption text-mute">
                        Distance mode: {summary.distance_mode.replace("_", "-")}
                        . Total sums only legs where both stops have
                        coordinates.
                      </p>

                      {summary.legs.length > 0 ? (
                        <ol className="space-y-1.5">
                          {summary.legs.map((leg) => (
                            <li
                              key={`${leg.from}-${leg.to}`}
                              className="flex flex-wrap items-center justify-between gap-2 type-small text-ink bg-stone/30 border border-sandstone/70 rounded-[6px] px-3 py-2"
                            >
                              <span className="min-w-0 break-words">
                                {stopName(leg.from)} → {stopName(leg.to)}
                              </span>
                              <span className="font-mono tabular-nums text-indigo shrink-0">
                                {leg.km.toFixed(1)} km
                              </span>
                            </li>
                          ))}
                        </ol>
                      ) : (
                        <p className="type-small text-mute">
                          No legs can be measured from the recorded
                          coordinates.
                        </p>
                      )}

                      {summary.top_features.length > 0 && (
                        <div className="space-y-1">
                          <span className="type-caption font-semibold text-ink block">
                            Verified features along this trail
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {summary.top_features.map((feature) => (
                              <span
                                key={feature}
                                className="type-caption bg-water/10 text-water border border-water/40 rounded-[6px] px-2 py-0.5"
                              >
                                {feature}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>

                {/* Stops */}
                <div className="bg-paper p-5 rounded-[10px] border border-sandstone space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-sandstone pb-2">
                    <h3 className="type-h3 text-indigo">Stops in order</h3>
                    {isMutating && (
                      <span className="type-caption text-mute">Saving...</span>
                    )}
                  </div>

                  {mutationError && (
                    <p className="type-small text-clay-red font-semibold">
                      {mutationError}
                    </p>
                  )}

                  {trail.stops.length === 0 ? (
                    <p className="type-small text-mute">
                      No stops yet. Add a heritage site below.
                    </p>
                  ) : (
                    <ol className="space-y-3">
                      {trail.stops.map((stop, index) => (
                        <li
                          key={stop.id}
                          className="border border-sandstone rounded-[6px] p-3 space-y-2"
                        >
                          <div className="flex items-start gap-3">
                            <span className="w-7 h-7 shrink-0 rounded-full bg-indigo text-paper flex items-center justify-center type-caption font-mono tabular-nums">
                              {stop.stop_order}
                            </span>
                            <div className="min-w-0 flex-1">
                              <Link
                                href={`/sites/${stop.site_id}`}
                                className="type-small font-semibold text-indigo hover:underline break-words"
                              >
                                {stop.site_name}
                              </Link>
                              <div className="type-caption text-mute">
                                {[stop.region, stop.category]
                                  .filter(Boolean)
                                  .join(" · ") || "Site details"}
                              </div>
                              <div className="type-caption text-mute">
                                {formatVisitDate(stop.visit_date)}
                              </div>
                              {stop.note && (
                                <p className="type-small text-ink mt-1 whitespace-pre-wrap break-words">
                                  {stop.note}
                                </p>
                              )}
                              {typeof stop.lat !== "number" ||
                              typeof stop.lon !== "number" ? (
                                <p className="type-caption text-turmeric mt-1">
                                  No coordinates recorded for this site.
                                </p>
                              ) : null}
                            </div>
                          </div>

                          <div className="flex flex-wrap gap-2 pl-10">
                            <button
                              type="button"
                              onClick={() => void handleMove(stop.id, -1)}
                              disabled={index === 0 || isMutating}
                              aria-label={`Move ${stop.site_name} up`}
                              className="px-2.5 py-1 bg-stone text-ink border border-sandstone rounded-[6px] type-caption font-semibold focus-ring disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                              ↑ Up
                            </button>
                            <button
                              type="button"
                              onClick={() => void handleMove(stop.id, 1)}
                              disabled={
                                index === trail.stops.length - 1 || isMutating
                              }
                              aria-label={`Move ${stop.site_name} down`}
                              className="px-2.5 py-1 bg-stone text-ink border border-sandstone rounded-[6px] type-caption font-semibold focus-ring disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                              ↓ Down
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                void handleRemoveStop(stop.id, stop.site_name)
                              }
                              disabled={isMutating}
                              aria-label={`Remove ${stop.site_name} from trail`}
                              className="px-2.5 py-1 bg-paper text-clay-red border border-clay-red/40 rounded-[6px] type-caption font-semibold focus-ring hover:bg-clay-red/5 disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                              Remove
                            </button>
                          </div>
                        </li>
                      ))}
                    </ol>
                  )}

                  {/* Add stop */}
                  <form
                    onSubmit={handleAddStop}
                    className="border-t border-sandstone pt-4 space-y-3"
                  >
                    <h4 className="type-small font-semibold text-ink">
                      Add a stop
                    </h4>

                    {stopError && (
                      <p className="type-small text-clay-red font-semibold">
                        {stopError}
                      </p>
                    )}
                    {stopMessage && (
                      <p className="type-small text-water font-semibold">
                        {stopMessage}
                      </p>
                    )}

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="space-y-1 sm:col-span-2">
                        <label
                          htmlFor="trail-stop-site"
                          className="type-caption font-semibold text-ink block"
                        >
                          Heritage site
                        </label>
                        {isLoadingSites ? (
                          <p className="type-caption text-mute">
                            Loading sites...
                          </p>
                        ) : sitesError ? (
                          <p className="type-caption text-clay-red">
                            {sitesError}
                          </p>
                        ) : (
                          <select
                            id="trail-stop-site"
                            value={stopSiteId}
                            onChange={(e) => setStopSiteId(e.target.value)}
                            className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3.5 py-2.5 type-small text-ink focus-ring"
                          >
                            <option value="">Pick a site</option>
                            {sites.map((site) => (
                              <option key={site.id} value={site.id}>
                                {site.name} ({site.region})
                              </option>
                            ))}
                          </select>
                        )}
                      </div>

                      <div className="space-y-1">
                        <label
                          htmlFor="trail-stop-date"
                          className="type-caption font-semibold text-ink block"
                        >
                          Visit date (optional)
                        </label>
                        <input
                          id="trail-stop-date"
                          type="date"
                          value={stopVisitDate}
                          onChange={(e) => setStopVisitDate(e.target.value)}
                          className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3 py-2 type-small text-ink focus-ring"
                        />
                      </div>

                      <div className="space-y-1">
                        <label
                          htmlFor="trail-stop-note"
                          className="type-caption font-semibold text-ink block"
                        >
                          Note (optional)
                        </label>
                        <input
                          id="trail-stop-note"
                          type="text"
                          value={stopNote}
                          onChange={(e) => setStopNote(e.target.value)}
                          placeholder="What did you record here?"
                          className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3 py-2 type-small text-ink placeholder:text-mute focus-ring"
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={isAddingStop || !stopSiteId}
                      className="px-5 py-2 bg-indigo text-paper rounded-[6px] type-small font-semibold focus-ring hover:bg-indigo/90 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isAddingStop ? "Adding..." : "Add stop"}
                    </button>
                  </form>
                </div>

                {/* Generated journal */}
                <div className="bg-paper p-5 rounded-[10px] border border-sandstone space-y-4">
                  <div className="flex flex-wrap items-center gap-2 border-b border-sandstone pb-2">
                    <h3 className="type-h3 text-indigo">Trail journal</h3>
                    <span className="type-caption bg-turmeric/10 text-turmeric border border-turmeric/40 rounded-[6px] px-2 py-0.5">
                      Generated summaries
                    </span>
                  </div>
                  <p className="type-caption text-mute">
                    Summaries are template-generated from stored site data.
                    They never replace your original notes.
                  </p>

                  {journalError && (
                    <p className="type-small text-clay-red font-semibold">
                      {journalError}
                    </p>
                  )}

                  {!journalError && !journal && (
                    <p className="type-small text-mute">Journal is loading...</p>
                  )}

                  {!journalError && journal && journal.entries.length === 0 && (
                    <p className="type-small text-mute">
                      Add a stop to generate journal entries.
                    </p>
                  )}

                  {!journalError && journal && journal.entries.length > 0 && (
                    <ol className="space-y-4">
                      {journal.entries.map((entry) => (
                        <li
                          key={`${entry.stop_order}-${entry.site_id}`}
                          className="space-y-2"
                        >
                          <div className="flex flex-wrap items-baseline gap-2">
                            <span className="type-small font-semibold text-ink">
                              {entry.stop_order}. {entry.site_name}
                            </span>
                            <span className="type-caption text-mute">
                              {formatVisitDate(entry.visit_date)} ·{" "}
                              {entry.photos}{" "}
                              {entry.photos === 1 ? "photo" : "photos"}
                            </span>
                          </div>

                          {entry.original_note && (
                            <div className="field-note-rule">
                              <span className="type-caption text-sandstone font-semibold uppercase tracking-wider block">
                                Original note
                              </span>
                              <p className="type-small text-ink whitespace-pre-wrap break-words">
                                {entry.original_note}
                              </p>
                            </div>
                          )}

                          <div className="bg-stone/30 border border-sandstone rounded-[6px] p-3 space-y-1">
                            <span className="type-caption text-turmeric font-semibold uppercase tracking-wider block">
                              Generated summary
                            </span>
                            <p className="type-small text-ink break-words">
                              {entry.generated_summary}
                            </p>
                          </div>

                          {entry.verified_features.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                              {entry.verified_features.map((feature) => (
                                <span
                                  key={feature}
                                  className="type-caption bg-water/10 text-water border border-water/40 rounded-[6px] px-2 py-0.5"
                                >
                                  {feature}
                                </span>
                              ))}
                            </div>
                          )}
                        </li>
                      ))}
                    </ol>
                  )}
                </div>
              </>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
