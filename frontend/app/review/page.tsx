"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { ProvenanceChip } from "@/components/ProvenanceChip";
import { getReviewQueue, reviewTag, addTag, resolveImageUrl } from "@/lib/api";
import type { ReviewQueueItem } from "@/lib/types";

export default function ReviewPage() {
  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [isActing, setIsActing] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Add tag modal state
  const [showAddTag, setShowAddTag] = useState<boolean>(false);
  const [addTagLabel, setAddTagLabel] = useState<string>("");
  const [addTagReviewer, setAddTagReviewer] = useState<string>("");
  const [addTagError, setAddTagError] = useState<string | null>(null);

  // Reviewer name persisted per session
  const [reviewer, setReviewer] = useState<string>("");
  const [showReviewerInput, setShowReviewerInput] = useState<boolean>(false);
  const addTagLabelRef = useRef<HTMLInputElement>(null);

  // Load queue on mount
  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const data = await getReviewQueue(50);
        if (!ignore) {
          setQueue(data);
          setIsLoading(false);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setLoadError(
            err instanceof Error
              ? err.message
              : "Could not load the review queue. Check your connection."
          );
          setIsLoading(false);
        }
      }
    }
    void load();
    return () => {
      ignore = true;
    };
  }, []);

  // Focus add-tag label input when modal opens
  useEffect(() => {
    if (showAddTag) {
      setTimeout(() => addTagLabelRef.current?.focus(), 50);
    }
  }, [showAddTag]);

  const currentItem: ReviewQueueItem | undefined = queue[currentIndex];
  const totalItems = queue.length;

  const handleConfirm = useCallback(async () => {
    if (!currentItem) return;
    if (!reviewer.trim()) {
      setShowReviewerInput(true);
      return;
    }
    setIsActing(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      await reviewTag(currentItem.id, "confirm", reviewer.trim());
      setActionSuccess(`Tag "${currentItem.label}" confirmed.`);
      setCurrentIndex((i) => Math.min(i + 1, totalItems - 1));
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Action failed. Try again.");
    } finally {
      setIsActing(false);
    }
  }, [currentItem, reviewer, totalItems]);

  const handleReject = useCallback(async () => {
    if (!currentItem) return;
    if (!reviewer.trim()) {
      setShowReviewerInput(true);
      return;
    }
    setIsActing(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      await reviewTag(currentItem.id, "reject", reviewer.trim());
      setActionSuccess(`Tag "${currentItem.label}" rejected.`);
      setCurrentIndex((i) => Math.min(i + 1, totalItems - 1));
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Action failed. Try again.");
    } finally {
      setIsActing(false);
    }
  }, [currentItem, reviewer, totalItems]);

  const handleAddTag = useCallback(async () => {
    if (!currentItem) return;
    const label = addTagLabel.trim();
    const rev = addTagReviewer.trim() || reviewer.trim();
    if (!label) { setAddTagError("Label is required."); return; }
    if (!rev) { setAddTagError("Reviewer name is required."); return; }
    setIsActing(true);
    setAddTagError(null);
    try {
      await addTag(currentItem.image_id, label, rev);
      setActionSuccess(`Tag "${label}" added.`);
      setShowAddTag(false);
      setAddTagLabel("");
      setAddTagReviewer("");
      setCurrentIndex((i) => Math.min(i + 1, totalItems - 1));
    } catch (err: unknown) {
      setAddTagError(err instanceof Error ? err.message : "Could not add tag. Try again.");
    } finally {
      setIsActing(false);
    }
  }, [currentItem, addTagLabel, addTagReviewer, reviewer, totalItems]);

  const isAllDone = totalItems > 0 && currentIndex >= totalItems;

  return (
    <div className="min-h-screen bg-stone flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8 sm:px-6 md:py-10 space-y-8">
        {/* Header */}
        <div>
          <h1 className="type-h1 text-indigo font-serif font-semibold">Review queue</h1>
          <p className="type-body text-mute mt-1">
            Human verification queue sorted by lowest similarity score first.
            Decisions are append-only — original field records are never overwritten.
          </p>
        </div>

        {/* Reviewer name prompt */}
        {showReviewerInput && (
          <div className="bg-paper p-5 rounded-[10px] border border-indigo/30 space-y-3">
            <p className="type-small font-semibold text-ink">
              Please enter your reviewer name before acting:
            </p>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="text"
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                placeholder="E.g. Dr. K. Mehta"
                autoFocus
                className="flex-1 bg-stone/40 border border-sandstone rounded-[6px] px-3.5 py-2 type-body text-ink placeholder:text-mute focus-ring"
              />
              <button
                type="button"
                onClick={() => setShowReviewerInput(false)}
                disabled={!reviewer.trim()}
                className="px-5 py-2 bg-indigo text-paper rounded-[6px] type-small font-semibold focus-ring hover:bg-indigo/90 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Save
              </button>
            </div>
          </div>
        )}

        {/* Reviewer name display */}
        {reviewer && !showReviewerInput && (
          <div className="flex items-center gap-2 type-caption text-mute">
            <span>Reviewing as:</span>
            <span className="font-semibold text-ink">{reviewer}</span>
            <button
              type="button"
              onClick={() => setShowReviewerInput(true)}
              className="text-indigo hover:underline focus-ring rounded px-1"
            >
              Change
            </button>
          </div>
        )}

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
              Verify that the backend is running and NEXT_PUBLIC_API_URL is configured.
            </div>
          </div>
        )}

        {/* Empty queue */}
        {!isLoading && !loadError && totalItems === 0 && (
          <div className="bg-paper p-8 rounded-[10px] border border-sandstone text-center space-y-3">
            <h2 className="type-h2 text-indigo">Queue is clear</h2>
            <p className="type-body text-mute">
              All AI-suggested tags have been reviewed. Check back after new photos are uploaded.
            </p>
          </div>
        )}

        {/* All items reviewed */}
        {!isLoading && !loadError && isAllDone && (
          <div className="bg-paper p-8 rounded-[10px] border border-water/40 text-center space-y-3">
            <h2 className="type-h2 text-water">Review session complete</h2>
            <p className="type-body text-mute">
              You&apos;ve reviewed all {totalItems} items in this session.
            </p>
          </div>
        )}

        {/* Action banner */}
        {actionSuccess && (
          <div className="bg-water/10 border border-water text-water p-4 rounded-[6px] type-small font-medium flex items-center justify-between">
            <span>{actionSuccess}</span>
            <button type="button" onClick={() => setActionSuccess(null)} className="text-water text-lg leading-none ml-3">&times;</button>
          </div>
        )}
        {actionError && (
          <div className="bg-clay-red/10 border border-clay-red text-clay-red p-4 rounded-[6px] type-small font-semibold">
            {actionError}
          </div>
        )}

        {/* Review card */}
        {!isLoading && !loadError && currentItem && !isAllDone && (
          <>
            {/* Progress bar */}
            <div className="flex items-center gap-3 type-caption text-mute">
              <span className="tabular-nums">Item {currentIndex + 1} of {totalItems}</span>
              <div className="flex-1 h-1.5 bg-stone rounded-full overflow-hidden">
                <div
                  className="h-full bg-indigo rounded-full transition-all duration-300"
                  style={{ width: `${((currentIndex + 1) / totalItems) * 100}%` }}
                />
              </div>
              <span className="tabular-nums">{Math.round(((currentIndex + 1) / totalItems) * 100)}%</span>
            </div>

            <div className="bg-paper rounded-[10px] border border-sandstone overflow-hidden">
              {/* Card header */}
              <div className="border-b border-sandstone px-6 py-4 flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-0.5">
                  <span className="type-caption text-mute block">
                    Tag #{currentItem.id} &middot; Image #{currentItem.image_id}
                  </span>
                  <h2 className="type-h2 text-indigo">Tag verification</h2>
                </div>
                <ProvenanceChip status="suggested" score={currentItem.score} label={currentItem.label} />
              </div>

              {/* Tag detail */}
              <div className="px-6 py-6 space-y-5">
                <div className="bg-stone/50 rounded-[8px] border border-sandstone p-5 space-y-2">
                  <div className="type-caption text-mute font-semibold uppercase tracking-wide">Suggested tag</div>
                  <div className="type-h2 text-ink">{currentItem.label}</div>
                  <div className="type-caption text-mute">
                    Type: <span className="font-semibold capitalize">{currentItem.tag_type.replace("_", " ")}</span>
                  </div>
                </div>

                <div className="field-note-rule">
                  <span className="type-caption text-sandstone font-semibold uppercase tracking-wider block mb-1">
                    Raw cosine similarity score
                  </span>
                  <div className="flex items-center gap-3">
                    <span className="font-mono tabular-nums text-lg font-semibold text-ink">
                      {currentItem.score.toFixed(2)}
                    </span>
                    <span className="type-caption text-mute">
                      Queued lowest-score-first. This is cosine similarity, not a probability.
                    </span>
                  </div>
                </div>

                {/* Linked image thumbnail (best-effort; hides on 404) */}
                <div className="space-y-1">
                  <div className="type-caption text-mute font-semibold">Image #{currentItem.image_id}</div>
                  <div className="w-full max-w-sm aspect-video bg-stone border border-sandstone rounded-none overflow-hidden flex items-center justify-center text-mute type-caption">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={resolveImageUrl(`/files/${currentItem.image_id}.jpg`)}
                      alt={`Image #${currentItem.image_id}`}
                      className="w-full h-full object-cover"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                  </div>
                </div>

                {/* Action buttons */}
                <div className="flex flex-wrap gap-3 pt-2 border-t border-sandstone">
                  <button
                    type="button"
                    id="review-confirm-btn"
                    onClick={() => void handleConfirm()}
                    disabled={isActing}
                    className="px-5 py-2 bg-water text-paper rounded-[6px] type-small font-semibold focus-ring hover:bg-water/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isActing ? "Saving..." : "Confirm"}
                  </button>
                  <button
                    type="button"
                    id="review-reject-btn"
                    onClick={() => void handleReject()}
                    disabled={isActing}
                    className="px-5 py-2 bg-paper text-clay-red border border-clay-red/40 rounded-[6px] type-small font-semibold focus-ring hover:bg-clay-red/5 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isActing ? "Saving..." : "Reject"}
                  </button>
                  <button
                    type="button"
                    id="review-add-tag-btn"
                    onClick={() => { setShowAddTag(true); setAddTagError(null); }}
                    disabled={isActing}
                    className="px-5 py-2 bg-stone text-ink border border-sandstone rounded-[6px] type-small font-semibold focus-ring hover:bg-paper disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Add tag
                  </button>
                  {currentIndex < totalItems - 1 && (
                    <button
                      type="button"
                      onClick={() => setCurrentIndex((i) => i + 1)}
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
                This is recorded as <span className="font-semibold">added_by_human</span> and
                will not overwrite original field notes.
              </div>

              {addTagError && (
                <div className="text-clay-red type-small font-semibold bg-clay-red/10 border border-clay-red/30 rounded-[6px] p-3">
                  {addTagError}
                </div>
              )}

              <div className="space-y-1">
                <label htmlFor="add-tag-label" className="type-caption font-semibold text-ink block">
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
                  onKeyDown={(e) => { if (e.key === "Enter") void handleAddTag(); }}
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="add-tag-reviewer" className="type-caption font-semibold text-ink block">
                  Your name:
                </label>
                <input
                  id="add-tag-reviewer"
                  type="text"
                  value={addTagReviewer || reviewer}
                  onChange={(e) => setAddTagReviewer(e.target.value)}
                  placeholder="Reviewer name"
                  className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3.5 py-2.5 type-body text-ink placeholder:text-mute focus-ring"
                />
              </div>

              <div className="flex gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => void handleAddTag()}
                  disabled={isActing || !addTagLabel.trim()}
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
