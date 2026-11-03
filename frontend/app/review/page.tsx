"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { ProvenanceChip } from "@/components/ProvenanceChip";
import {
  addTag,
  getReviewers,
  getReviewHistory,
  getReviewQueue,
  resolveImageUrl,
  reviewTag,
} from "@/lib/api";
import type {
  ReviewHistoryEntry,
  ReviewQueueItem,
  TagStatus,
} from "@/lib/types";

const STATUS_TABS: { value: TagStatus; label: string }[] = [
  { value: "auto", label: "Pending" },
  { value: "verified", label: "Verified" },
  { value: "rejected", label: "Rejected" },
  { value: "added_by_human", label: "Human-added" },
];

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function statusLabel(status: string): string {
  return status.replace(/_/g, " ");
}

export default function ReviewPage() {
  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<TagStatus>("auto");
  const [reloadKey, setReloadKey] = useState<number>(0);

  const [reviewers, setReviewers] = useState<string[]>([]);
  const [reviewersError, setReviewersError] = useState<string | null>(null);
  const [reviewer, setReviewer] = useState<string>("");

  const [isActing, setIsActing] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Add tag modal state
  const [showAddTag, setShowAddTag] = useState<boolean>(false);
  const [addTagLabel, setAddTagLabel] = useState<string>("");
  const [addTagError, setAddTagError] = useState<string | null>(null);
  const addTagLabelRef = useRef<HTMLInputElement>(null);

  // Append-only history for one tag
  const [historyTagId, setHistoryTagId] = useState<number | null>(null);
  const [history, setHistory] = useState<ReviewHistoryEntry[] | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const [failedImageIds, setFailedImageIds] = useState<Set<number>>(
    () => new Set()
  );

  // Load the fixed demo reviewer identifiers
  useEffect(() => {
    let ignore = false;
    getReviewers()
      .then((data) => {
        if (ignore) return;
        setReviewers(data);
        setReviewer((current) => current || data[0] || "");
      })
      .catch((err: unknown) => {
        if (!ignore) {
          setReviewersError(
            err instanceof Error
              ? err.message
              : "Could not load the reviewer list."
          );
        }
      });
    return () => {
      ignore = true;
    };
  }, []);

  // Load the queue for the selected status
  useEffect(() => {
    let ignore = false;

    async function loadQueue() {
      setIsLoading(true);
      setLoadError(null);
      try {
        const data = await getReviewQueue(50, statusFilter);
        if (!ignore) {
          setQueue(data);
          setCurrentIndex(0);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setLoadError(
            err instanceof Error
              ? err.message
              : "Could not load the review queue. Check your connection."
          );
        }
      } finally {
        if (!ignore) setIsLoading(false);
      }
    }

    void loadQueue();
    return () => {
      ignore = true;
    };
  }, [statusFilter, reloadKey]);

  // Focus add-tag label input when modal opens
  useEffect(() => {
    if (showAddTag) {
      setTimeout(() => addTagLabelRef.current?.focus(), 50);
    }
  }, [showAddTag]);

  const currentItem: ReviewQueueItem | undefined = queue[currentIndex];
  const totalItems = queue.length;

  const loadHistory = useCallback(async (tagId: number) => {
    setHistoryTagId(tagId);
    setHistory(null);
    setHistoryError(null);
    setIsLoadingHistory(true);
    try {
      const rows = await getReviewHistory(tagId);
      setHistory(rows);
    } catch (err: unknown) {
      setHistoryError(
        err instanceof Error ? err.message : "Could not load review history."
      );
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  const handleReview = useCallback(
    async (action: "confirm" | "reject") => {
      if (!currentItem) return;
      if (!reviewer) {
        setActionError("Pick a reviewer before acting.");
        return;
      }

      setIsActing(true);
      setActionError(null);
      setActionSuccess(null);
      try {
        await reviewTag(currentItem.id, action, reviewer);
        setActionSuccess(
          `Tag "${currentItem.label}" ${
            action === "confirm" ? "verified" : "rejected"
          }.`
        );
        await loadHistory(currentItem.id);
        setReloadKey((value) => value + 1);
      } catch (err: unknown) {
        setActionError(
          err instanceof Error ? err.message : "Action failed. Try again."
        );
      } finally {
        setIsActing(false);
      }
    },
    [currentItem, reviewer, loadHistory]
  );

  const handleAddTag = useCallback(async () => {
    if (!currentItem) return;
    const label = addTagLabel.trim();
    if (!label) {
      setAddTagError("Label is required.");
      return;
    }
    if (!reviewer) {
      setAddTagError("Pick a reviewer before adding a tag.");
      return;
    }

    setIsActing(true);
    setAddTagError(null);
    try {
      const result = await addTag(currentItem.image_id, label, reviewer);
      setActionSuccess(`Tag "${label}" added as human-confirmed.`);
      setShowAddTag(false);
      setAddTagLabel("");
      await loadHistory(result.id);
      setReloadKey((value) => value + 1);
    } catch (err: unknown) {
      setAddTagError(
        err instanceof Error ? err.message : "Could not add tag. Try again."
      );
    } finally {
      setIsActing(false);
    }
  }, [currentItem, addTagLabel, reviewer, loadHistory]);

  const emptyMessage =
    statusFilter === "auto"
      ? "All AI-suggested tags have been reviewed. Check back after new photos are uploaded."
      : `No tags with status "${statusLabel(statusFilter)}" are available.`;

  return (
    <div className="min-h-screen bg-stone flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8 sm:px-6 md:py-10 space-y-8">
        {/* Header */}
        <div>
          <h1 className="type-h1 text-indigo font-serif font-semibold">
            Review queue
          </h1>
          <p className="type-body text-mute mt-1">
            Human verification queue sorted by lowest similarity score first.
            Decisions are append-only — original field records are never
            overwritten.
          </p>
        </div>

        {/* Reviewer select */}
        <div className="bg-paper p-4 rounded-[10px] border border-sandstone space-y-2">
          <div className="flex flex-col sm:flex-row sm:items-end gap-3">
            <div className="space-y-1 sm:max-w-xs w-full">
              <label
                htmlFor="reviewer-select"
                className="type-caption font-semibold text-ink block"
              >
                Reviewing as
              </label>
              <select
                id="reviewer-select"
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                disabled={reviewers.length === 0}
                className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3.5 py-2 type-small text-ink focus-ring disabled:opacity-50"
              >
                {reviewers.length === 0 && (
                  <option value="">Loading reviewers...</option>
                )}
                {reviewers.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
            <p className="type-caption text-mute sm:pb-2">
              Demo audit label only — not authentication. Reviewer identity can
              be impersonated until real auth is added.
            </p>
          </div>
          {reviewersError && (
            <p className="type-small text-clay-red font-semibold">
              Reviewer list unavailable: {reviewersError}
            </p>
          )}
        </div>

        {/* Status tabs */}
        <div className="flex flex-wrap gap-1 bg-paper p-2 rounded-[8px] border border-sandstone">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.value}
              type="button"
              onClick={() => setStatusFilter(tab.value)}
              aria-pressed={statusFilter === tab.value}
              className={`px-3 py-1.5 rounded-[6px] type-caption font-semibold transition-colors focus-ring ${
                statusFilter === tab.value
                  ? "bg-indigo text-paper"
                  : "text-ink hover:bg-stone/60"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Loading skeleton */}
        {isLoading && (
          <div className="bg-paper p-8 rounded-[10px] border border-sandstone space-y-4 animate-pulse">
            <div className="h-5 bg-stone/60 rounded-[6px] w-1/3" />
            <div className="h-16 bg-stone/60 rounded-[6px]" />
            <div className="flex gap-3">
              <div className="h-10 bg-stone/60 rounded-[6px] w-24" />
              <div className="h-10 bg-stone/60 rounded-[6px] w-24" />
            </div>
          </div>
        )}

        {/* Load error */}
        {!isLoading && loadError && (
          <div className="bg-paper p-8 rounded-[10px] border border-clay-red/40 text-center space-y-3">
            <h2 className="type-h2 text-clay-red">Queue unavailable</h2>
            <p className="type-body text-ink">{loadError}</p>
            <div className="type-caption text-mute">
              Verify that the backend is running and NEXT_PUBLIC_API_URL is
              configured.
            </div>
            <button
              type="button"
              onClick={() => setReloadKey((value) => value + 1)}
              className="px-4 py-2 bg-indigo text-paper rounded-[6px] type-small font-semibold focus-ring"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty queue */}
        {!isLoading && !loadError && totalItems === 0 && (
          <div className="bg-paper p-8 rounded-[10px] border border-sandstone text-center space-y-3">
            <h2 className="type-h2 text-indigo">Nothing to show</h2>
            <p className="type-body text-mute">{emptyMessage}</p>
          </div>
        )}

        {/* Action banner */}
        {actionSuccess && (
          <div className="bg-water/10 border border-water text-water p-4 rounded-[6px] type-small font-medium flex items-center justify-between">
            <span>{actionSuccess}</span>
            <button
              type="button"
              onClick={() => setActionSuccess(null)}
              aria-label="Dismiss success message"
              className="text-water text-lg leading-none ml-3"
            >
              &times;
            </button>
          </div>
        )}
        {actionError && (
          <div className="bg-clay-red/10 border border-clay-red text-clay-red p-4 rounded-[6px] type-small font-semibold">
            {actionError}
          </div>
        )}

        {/* Review card */}
        {!isLoading && !loadError && currentItem && (
          <>
            {/* Progress bar */}
            <div className="flex items-center gap-3 type-caption text-mute">
              <span className="tabular-nums">
                Item {currentIndex + 1} of {totalItems}
              </span>
              <div className="flex-1 h-1.5 bg-stone rounded-full overflow-hidden">
                <div
                  className="h-full bg-indigo rounded-full transition-all duration-300"
                  style={{
                    width: `${((currentIndex + 1) / totalItems) * 100}%`,
                  }}
                />
              </div>
              <span className="tabular-nums">
                {Math.round(((currentIndex + 1) / totalItems) * 100)}%
              </span>
            </div>

            <div className="bg-paper rounded-[10px] border border-sandstone overflow-hidden">
              {/* Card header */}
              <div className="border-b border-sandstone px-4 sm:px-6 py-4 flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-0.5">
                  <span className="type-caption text-mute block">
                    Tag #{currentItem.id} &middot; Image #{currentItem.image_id}
                  </span>
                  <h2 className="type-h2 text-indigo">Tag verification</h2>
                </div>
                <ProvenanceChip
                  status={currentItem.status}
                  score={currentItem.score}
                  label={currentItem.label}
                />
              </div>

              {/* Tag detail */}
              <div className="px-4 sm:px-6 py-6 space-y-5">
                <div className="bg-stone/50 rounded-[8px] border border-sandstone p-5 space-y-2">
                  <div className="type-caption text-mute font-semibold uppercase tracking-wide">
                    {currentItem.status === "auto"
                      ? "Suggested tag"
                      : `Tag (${statusLabel(currentItem.status)})`}
                  </div>
                  <div className="type-h2 text-ink break-words">
                    {currentItem.label}
                  </div>
                  <div className="type-caption text-mute">
                    Type:{" "}
                    <span className="font-semibold capitalize">
                      {currentItem.tag_type.replace("_", " ")}
                    </span>
                  </div>
                </div>

                <div className="field-note-rule">
                  <span className="type-caption text-sandstone font-semibold uppercase tracking-wider block mb-1">
                    Raw cosine similarity score
                  </span>
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="font-mono tabular-nums text-lg font-semibold text-ink">
                      {typeof currentItem.score === "number"
                        ? currentItem.score.toFixed(2)
                        : "not scored"}
                    </span>
                    <span className="type-caption text-mute">
                      {typeof currentItem.score === "number"
                        ? "Queued lowest-score-first. This is cosine similarity, not a probability."
                        : "Human-added tags have no model score."}
                    </span>
                  </div>
                </div>

                {/* Linked image and attribution */}
                <div className="space-y-2">
                  <div className="type-caption text-mute font-semibold">
                    Image #{currentItem.image_id}
                  </div>
                  <div className="w-full max-w-sm aspect-video bg-stone border border-sandstone rounded-none overflow-hidden flex items-center justify-center text-mute type-caption">
                    {currentItem.url &&
                    !failedImageIds.has(currentItem.id) ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={resolveImageUrl(currentItem.url)}
                        alt={`${currentItem.site_name} — tag ${currentItem.label}`}
                        className="w-full h-full object-cover"
                        onError={() =>
                          setFailedImageIds((current) => {
                            const next = new Set(current);
                            next.add(currentItem.id);
                            return next;
                          })
                        }
                      />
                    ) : (
                      <span>Image unavailable</span>
                    )}
                  </div>
                  <div className="type-caption text-mute flex flex-wrap gap-x-3 gap-y-1">
                    <Link
                      href={`/sites/${currentItem.site_id}`}
                      className="text-indigo font-semibold hover:underline"
                    >
                      {currentItem.site_name}
                    </Link>
                    {currentItem.author && (
                      <span>Photo: {currentItem.author}</span>
                    )}
                    {currentItem.licence && (
                      <span>Licence: {currentItem.licence}</span>
                    )}
                    {currentItem.source_url && (
                      <a
                        href={currentItem.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-indigo hover:underline"
                      >
                        Source
                      </a>
                    )}
                  </div>
                </div>

                {/* Action buttons */}
                <div className="flex flex-wrap gap-3 pt-2 border-t border-sandstone">
                  <button
                    type="button"
                    id="review-confirm-btn"
                    onClick={() => void handleReview("confirm")}
                    disabled={isActing || !reviewer}
                    className="px-5 py-2 bg-water text-paper rounded-[6px] type-small font-semibold focus-ring hover:bg-water/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isActing ? "Saving..." : "Confirm"}
                  </button>
                  <button
                    type="button"
                    id="review-reject-btn"
                    onClick={() => void handleReview("reject")}
                    disabled={isActing || !reviewer}
                    className="px-5 py-2 bg-paper text-clay-red border border-clay-red/40 rounded-[6px] type-small font-semibold focus-ring hover:bg-clay-red/5 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isActing ? "Saving..." : "Reject"}
                  </button>
                  <button
                    type="button"
                    id="review-add-tag-btn"
                    onClick={() => {
                      setShowAddTag(true);
                      setAddTagError(null);
                    }}
                    disabled={isActing || !reviewer}
                    className="px-5 py-2 bg-stone text-ink border border-sandstone rounded-[6px] type-small font-semibold focus-ring hover:bg-paper disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Add tag
                  </button>
                  <button
                    type="button"
                    onClick={() => void loadHistory(currentItem.id)}
                    className="px-5 py-2 bg-paper text-indigo border border-sandstone rounded-[6px] type-small font-semibold focus-ring hover:bg-stone transition-colors"
                  >
                    View history
                  </button>
                  {currentIndex < totalItems - 1 && (
                    <button
                      type="button"
                      onClick={() => setCurrentIndex((index) => index + 1)}
                      className="ml-auto px-4 py-2 text-mute type-small hover:text-ink focus-ring rounded-[6px]"
                    >
                      Skip →
                    </button>
                  )}
                </div>
              </div>
            </div>
          </>
        )}

        {/* Append-only history */}
        {historyTagId !== null && (
          <section
            aria-label="Review history"
            className="bg-paper p-5 rounded-[10px] border border-sandstone space-y-3"
          >
            <div className="flex items-center justify-between gap-2 border-b border-sandstone pb-2">
              <h2 className="type-h3 text-indigo">
                Review history for tag #{historyTagId}
              </h2>
              <button
                type="button"
                onClick={() => {
                  setHistoryTagId(null);
                  setHistory(null);
                  setHistoryError(null);
                }}
                className="type-caption text-mute hover:text-ink focus-ring rounded px-1"
              >
                Close
              </button>
            </div>

            {isLoadingHistory && (
              <p className="type-small text-mute">Loading history...</p>
            )}

            {!isLoadingHistory && historyError && (
              <p className="type-small text-clay-red font-semibold">
                {historyError}
              </p>
            )}

            {!isLoadingHistory &&
              !historyError &&
              history &&
              history.length === 0 && (
                <p className="type-small text-mute">
                  No review actions recorded for this tag yet.
                </p>
              )}

            {!isLoadingHistory &&
              !historyError &&
              history &&
              history.length > 0 && (
                <ol className="space-y-2">
                  {history.map((entry) => (
                    <li
                      key={entry.id}
                      className="border border-sandstone/70 rounded-[6px] px-3 py-2 bg-stone/30 space-y-0.5"
                    >
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <span className="type-small font-semibold text-ink capitalize">
                          {entry.action}
                        </span>
                        <span className="type-caption text-mute">
                          by {entry.reviewer}
                        </span>
                        <span className="type-caption text-mute">
                          {statusLabel(entry.previous_status ?? "none")} →{" "}
                          {statusLabel(entry.new_status ?? "none")}
                        </span>
                      </div>
                      <time className="type-caption text-mute block">
                        {formatTimestamp(entry.created_at)}
                      </time>
                    </li>
                  ))}
                </ol>
              )}
          </section>
        )}

        {/* Add tag modal */}
        {showAddTag && currentItem && (
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Add a human tag"
            className="fixed inset-0 z-50 bg-ink/40 flex items-center justify-center p-4"
          >
            <div className="bg-paper rounded-[12px] border border-sandstone shadow-lg w-full max-w-md p-6 space-y-5">
              <div className="flex items-center justify-between">
                <h2 className="type-h2 text-indigo">Add human tag</h2>
                <button
                  type="button"
                  onClick={() => setShowAddTag(false)}
                  aria-label="Close dialog"
                  className="text-mute hover:text-ink text-xl leading-none focus-ring rounded px-1"
                >
                  &times;
                </button>
              </div>

              <div className="type-caption text-mute">
                Adding a human-confirmed tag to image #{currentItem.image_id}.
                This is recorded as{" "}
                <span className="font-semibold">added_by_human</span> and will
                not overwrite original field notes.
              </div>

              {addTagError && (
                <div className="text-clay-red type-small font-semibold bg-clay-red/10 border border-clay-red/30 rounded-[6px] p-3">
                  {addTagError}
                </div>
              )}

              <div className="space-y-1">
                <label
                  htmlFor="add-tag-label"
                  className="type-caption font-semibold text-ink block"
                >
                  Architectural tag label:
                </label>
                <input
                  ref={addTagLabelRef}
                  id="add-tag-label"
                  type="text"
                  value={addTagLabel}
                  onChange={(e) => setAddTagLabel(e.target.value)}
                  placeholder="E.g. carved jharokhas, domes, bastions..."
                  className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3.5 py-2.5 type-body text-ink placeholder:text-mute focus-ring"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void handleAddTag();
                  }}
                />
              </div>

              <p className="type-caption text-mute">
                Recorded as:{" "}
                <span className="font-semibold text-ink">
                  {reviewer || "no reviewer selected"}
                </span>
              </p>

              <div className="flex gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => void handleAddTag()}
                  disabled={isActing || !addTagLabel.trim() || !reviewer}
                  className="flex-1 py-2.5 bg-indigo text-paper rounded-[6px] type-small font-semibold focus-ring hover:bg-indigo/90 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isActing ? "Saving..." : "Add tag"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddTag(false)}
                  className="px-5 py-2.5 bg-stone text-ink border border-sandstone rounded-[6px] type-small focus-ring hover:bg-paper"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
