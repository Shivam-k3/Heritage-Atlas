"use client";

import React, { useState, useRef, useCallback } from "react";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import {
  searchImages,
  searchText,
  searchByImage,
  resolveImageUrl,
  formatSimilarityScore,
} from "@/lib/api";
import { ProvenanceChip } from "@/components/ProvenanceChip";
import type { ImageSearchResult, TextSearchResult } from "@/lib/types";

/** Per-image provenance and attribution returned by the image search endpoints. */
function ResultAttribution({ item }: { item: ImageSearchResult }) {
  const hasTags = item.tags && item.tags.length > 0;
  const hasCredit = Boolean(item.author || item.licence || item.source_url);
  if (!hasTags && !hasCredit) return null;

  return (
    <div className="space-y-1">
      {hasTags && (
        <div className="flex flex-wrap gap-1.5">
          {item.tags?.map((tag) => (
            <ProvenanceChip
              key={tag.id}
              status={tag.status}
              label={tag.label}
              score={tag.score}
            />
          ))}
        </div>
      )}
      {hasCredit && (
        <div className="type-caption text-mute flex flex-wrap gap-x-2 gap-y-1">
          {item.author && <span>Photo: {item.author}</span>}
          {item.licence && <span>Licence: {item.licence}</span>}
          {item.source_url && (
            <a
              href={item.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo hover:underline"
            >
              Source
            </a>
          )}
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  const [mode, setMode] = useState<"describe" | "photo">("describe");

  // Describe mode states
  const [query, setQuery] = useState<string>("");
  const [isSearchingDescribe, setIsSearchingDescribe] = useState<boolean>(false);
  const [describeSearched, setDescribeSearched] = useState<boolean>(false);
  const [describeError, setDescribeError] = useState<string | null>(null);
  const [imageResults, setImageResults] = useState<ImageSearchResult[]>([]);
  const [textResults, setTextResults] = useState<TextSearchResult[]>([]);

  // Photo mode states
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isSearchingPhoto, setIsSearchingPhoto] = useState<boolean>(false);
  const [photoSearched, setPhotoSearched] = useState<boolean>(false);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const [photoResults, setPhotoResults] = useState<ImageSearchResult[]>([]);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Handle Describe search execution
  const handleDescribeSearch = useCallback(
    async (e?: React.FormEvent) => {
      if (e) e.preventDefault();
      const trimmed = query.trim();
      if (!trimmed) return;

      setIsSearchingDescribe(true);
      setDescribeError(null);
      setDescribeSearched(true);

      try {
        const [imgs, texts] = await Promise.all([
          searchImages(trimmed, 12),
          searchText(trimmed, 6),
        ]);
        setImageResults(imgs);
        setTextResults(texts);
      } catch (err: unknown) {
        setDescribeError(
          err instanceof Error
            ? err.message
            : "Search query failed. Check your connection or try another term."
        );
      } finally {
        setIsSearchingDescribe(false);
      }
    },
    [query]
  );

  // Handle file selection for Photo mode
  const handleFileSelect = (file: File) => {
    if (!file.type.startsWith("image/")) {
      setPhotoError("Please select an image file (JPEG, PNG, WebP).");
      return;
    }
    setSelectedFile(file);
    setPhotoError(null);
    setPhotoSearched(false);
    setPhotoResults([]);

    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  // Handle Photo search execution
  const handlePhotoSearch = useCallback(async () => {
    if (!selectedFile) return;

    setIsSearchingPhoto(true);
    setPhotoError(null);
    setPhotoSearched(true);

    try {
      const results = await searchByImage(selectedFile, 12);
      setPhotoResults(results);
    } catch (err: unknown) {
      setPhotoError(
        err instanceof Error
          ? err.message
          : "Visual search failed. Check your connection or try another photo."
      );
    } finally {
      setIsSearchingPhoto(false);
    }
  }, [selectedFile]);

  return (
    <div className="min-h-screen bg-stone flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-8 sm:px-6 md:py-10 space-y-8">
        {/* Header */}
        <div>
          <h1 className="type-h1 text-indigo font-serif font-semibold">Search</h1>
          <p className="type-body text-mute mt-1">
            Explore heritage sites by architectural description or find visually similar structures by photo.
          </p>
        </div>

        {/* Mode Toggle per DESIGN.md Section 8.2 */}
        <div className="bg-paper p-2 rounded-[8px] border border-sandstone flex items-center gap-1 self-start max-w-sm">
          <button
            type="button"
            onClick={() => setMode("describe")}
            aria-pressed={mode === "describe"}
            className={`flex-1 py-2 px-4 rounded-[6px] type-small font-semibold transition-colors focus-ring text-center ${
              mode === "describe"
                ? "bg-indigo text-paper"
                : "text-ink hover:bg-stone/50"
            }`}
          >
            Describe
          </button>
          <button
            type="button"
            onClick={() => setMode("photo")}
            aria-pressed={mode === "photo"}
            className={`flex-1 py-2 px-4 rounded-[6px] type-small font-semibold transition-colors focus-ring text-center ${
              mode === "photo"
                ? "bg-indigo text-paper"
                : "text-ink hover:bg-stone/50"
            }`}
          >
            Photo
          </button>
        </div>

        {/* ------------------------------------------------------------- */}
        {/* MODE 1: DESCRIBE (calls /search/images and /search/text)       */}
        {/* ------------------------------------------------------------- */}
        {mode === "describe" && (
          <div className="space-y-8">
            {/* Search Input Box */}
            <form
              onSubmit={handleDescribeSearch}
              className="bg-paper p-5 sm:p-6 rounded-[10px] border border-sandstone space-y-3"
            >
              <label htmlFor="search-describe-input" className="type-small font-semibold text-ink block">
                Architectural description or feature
              </label>
              <div className="flex flex-col sm:flex-row gap-2.5">
                <div className="relative flex-1">
                  <input
                    id="search-describe-input"
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="E.g. carved pillars, subterranean stepwell, rounded bastions..."
                    className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3.5 py-2.5 type-body text-ink placeholder:text-mute focus-ring transition-colors"
                  />
                  {query && (
                    <button
                      type="button"
                      onClick={() => setQuery("")}
                      aria-label="Clear query"
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-mute hover:text-ink text-lg"
                    >
                      &times;
                    </button>
                  )}
                </div>
                <button
                  type="submit"
                  disabled={isSearchingDescribe || !query.trim()}
                  className="px-6 py-2.5 bg-indigo text-paper rounded-[6px] type-small font-semibold focus-ring hover:bg-indigo/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isSearchingDescribe ? "Searching..." : "Search"}
                </button>
              </div>
              <div className="type-caption text-mute">
                Dual neural search: CLIP retrieves matching photography while MiniLM ranks original field notes.
              </div>
            </form>

            {/* Loading State */}
            {isSearchingDescribe && (
              <div className="p-8 text-center space-y-4 bg-paper rounded-[10px] border border-sandstone">
                <div className="w-8 h-8 border-3 border-sandstone border-t-indigo rounded-full animate-spin mx-auto" />
                <div className="type-small text-mute">Analyzing embeddings across photographs and field notes...</div>
              </div>
            )}

            {/* Error State per DESIGN.md */}
            {!isSearchingDescribe && describeError && (
              <div className="bg-paper p-6 rounded-[10px] border border-clay-red/40 text-center space-y-2">
                <div className="text-clay-red type-small font-semibold">{describeError}</div>
                <div className="type-caption text-mute">Check your backend connection or verify that NEXT_PUBLIC_API_URL is reachable.</div>
              </div>
            )}

            {/* Empty State per DESIGN.md */}
            {!isSearchingDescribe &&
              !describeError &&
              describeSearched &&
              imageResults.length === 0 &&
              textResults.length === 0 && (
                <div className="bg-paper p-8 rounded-[10px] border border-sandstone text-center space-y-3">
                  <p className="type-body text-ink">
                    No matching results found for this query. Try different architectural features or clear filters.
                  </p>
                </div>
              )}

            {/* Results: Matching Photos from /search/images */}
            {!isSearchingDescribe && !describeError && imageResults.length > 0 && (
              <section aria-label="Matching photos" className="space-y-4">
                <div className="flex items-center justify-between border-b border-sandstone pb-2">
                  <h2 className="type-h2 text-indigo">Matching photos</h2>
                  <span className="type-caption text-mute tabular-nums">
                    {imageResults.length} matching {imageResults.length === 1 ? "photo" : "photos"}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                  {imageResults.map((item) => (
                    <article
                      key={item.image_id}
                      className="bg-paper border border-sandstone rounded-none overflow-hidden flex flex-col"
                    >
                      {/* Photo leads with radius 0 */}
                      <Link
                        href={`/sites/${item.site_id}`}
                        className="block aspect-video bg-stone overflow-hidden border-b border-sandstone focus-ring"
                        title={`View ${item.name}`}
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={resolveImageUrl(item.url)}
                          alt={item.name}
                          className="w-full h-full object-cover rounded-none hover:scale-105 transition-transform duration-200"
                        />
                      </Link>

                      <div className="p-3.5 space-y-2 flex-1 flex flex-col justify-between">
                        <div>
                          <Link
                            href={`/sites/${item.site_id}`}
                            className="font-serif font-semibold text-ink text-[17px] leading-[22px] hover:text-indigo hover:underline block"
                          >
                            {item.name}
                          </Link>
                          <div className="type-caption text-mute mt-0.5">{item.region}</div>
                          <ResultAttribution item={item} />
                        </div>

                        {/* Raw similarity score badge & why line strictly from API data per Task 6 */}
                        <div className="pt-2 border-t border-sandstone/40 space-y-1">
                          <div className="flex items-center justify-between text-[13px]">
                            <span className="text-mute">Similarity:</span>
                            <span
                              title="Similarity to the query, not a probability."
                              className="font-mono text-xs tabular-nums font-semibold px-2 py-0.5 rounded-[4px] bg-stone text-indigo border border-sandstone/50 cursor-help"
                            >
                              {formatSimilarityScore(item.score)}
                            </span>
                          </div>
                          {/* "Why" line: Only uses data the API actually returns; no invented tags */}
                          <div className="type-caption text-mute truncate" title={`Cosine score: ${formatSimilarityScore(item.score)}`}>
                            Score: {formatSimilarityScore(item.score)} cosine similarity to query
                          </div>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            )}

            {/* Results: Matching Site Notes from /search/text */}
            {!isSearchingDescribe && !describeError && textResults.length > 0 && (
              <section aria-label="Matching site notes" className="space-y-4 pt-4 border-t border-sandstone">
                <div className="flex items-center justify-between border-b border-sandstone pb-2">
                  <h2 className="type-h2 text-indigo">Matching site notes</h2>
                  <span className="type-caption text-mute tabular-nums">
                    {textResults.length} matching {textResults.length === 1 ? "site note" : "site notes"}
                  </span>
                </div>

                <div className="space-y-3">
                  {textResults.map((item) => (
                    <div
                      key={item.id}
                      className="bg-paper p-5 rounded-[10px] border border-sandstone space-y-2.5"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <Link
                            href={`/sites/${item.id}`}
                            className="font-serif font-semibold text-indigo text-lg hover:underline block"
                          >
                            {item.name}
                          </Link>
                          <span className="type-caption text-mute">{item.region}</span>
                        </div>
                        <span
                          title="Similarity to the query, not a probability."
                          className="font-mono text-xs tabular-nums font-semibold px-2 py-0.5 rounded-[4px] bg-stone text-indigo border border-sandstone/50 shrink-0 cursor-help"
                        >
                          {formatSimilarityScore(item.score)}
                        </span>
                      </div>

                      {/* Field note under 3 px sandstone rule */}
                      <div className="field-note-rule">
                        <p className="type-small text-ink line-clamp-3">
                          {item.description}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* MODE 2: PHOTO (calls /search/by-image)                        */}
        {/* ------------------------------------------------------------- */}
        {mode === "photo" && (
          <div className="space-y-8">
            {/* Drag & drop upload zone */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={`bg-paper p-8 rounded-[10px] border-2 border-dashed transition-colors text-center space-y-4 ${
                isDragging ? "border-indigo bg-indigo/5" : "border-sandstone"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileSelect(e.target.files[0]);
                  }
                }}
                className="hidden"
                id="photo-search-input"
              />

              {previewUrl ? (
                <div className="space-y-4">
                  <div className="max-w-xs mx-auto aspect-video bg-stone border border-sandstone rounded-none overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={previewUrl}
                      alt="Selected query preview"
                      className="w-full h-full object-cover rounded-none"
                    />
                  </div>
                  <div className="type-small text-ink font-medium">
                    {selectedFile?.name}{" "}
                    <span className="text-mute">
                      ({selectedFile ? (selectedFile.size / 1024).toFixed(0) : 0} KB)
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center justify-center gap-3">
                    <button
                      type="button"
                      onClick={handlePhotoSearch}
                      disabled={isSearchingPhoto}
                      className="px-6 py-2.5 bg-indigo text-paper rounded-[6px] type-small font-semibold focus-ring hover:bg-indigo/90 disabled:opacity-50"
                    >
                      {isSearchingPhoto ? "Searching with photo..." : "Search with this photo"}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedFile(null);
                        setPreviewUrl(null);
                        setPhotoResults([]);
                        setPhotoSearched(false);
                      }}
                      className="px-4 py-2 bg-paper text-mute border border-sandstone rounded-[6px] type-small hover:bg-stone focus-ring"
                    >
                      Change photo
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <svg
                    className="w-12 h-12 text-sandstone mx-auto"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                    <circle cx="8.5" cy="8.5" r="1.5" />
                    <polyline points="21 15 16 10 5 21" />
                  </svg>
                  <div className="type-body font-semibold text-ink">
                    Drag and drop a heritage photo, or click to browse
                  </div>
                  <div className="type-caption text-mute">
                    Upload a field photo to find visually similar stone architecture. Accepts JPEG, PNG, WebP.
                  </div>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="px-5 py-2 bg-paper border border-sandstone text-indigo rounded-[6px] type-small font-semibold hover:bg-stone focus-ring"
                  >
                    Select photo
                  </button>
                </div>
              )}
            </div>

            {/* Loading State */}
            {isSearchingPhoto && (
              <div className="p-8 text-center space-y-4 bg-paper rounded-[10px] border border-sandstone">
                <div className="w-8 h-8 border-3 border-sandstone border-t-indigo rounded-full animate-spin mx-auto" />
                <div className="type-small text-mute">Encoding photo with CLIP and comparing visual embeddings...</div>
              </div>
            )}

            {/* Error State */}
            {!isSearchingPhoto && photoError && (
              <div className="bg-paper p-6 rounded-[10px] border border-clay-red/40 text-center space-y-2">
                <div className="text-clay-red type-small font-semibold">{photoError}</div>
                <div className="type-caption text-mute">Check that the image is valid and the backend service is running.</div>
              </div>
            )}

            {/* Empty State */}
            {!isSearchingPhoto &&
              !photoError &&
              photoSearched &&
              photoResults.length === 0 && (
                <div className="bg-paper p-8 rounded-[10px] border border-sandstone text-center space-y-3">
                  <p className="type-body text-ink">
                    No visually similar sites found for this photo. Try another photograph or angle.
                  </p>
                </div>
              )}

            {/* Visual Search Results */}
            {!isSearchingPhoto && !photoError && photoResults.length > 0 && (
              <section aria-label="Visually similar photos" className="space-y-4">
                <div className="flex items-center justify-between border-b border-sandstone pb-2">
                  <h2 className="type-h2 text-indigo">Visually similar architecture</h2>
                  <span className="type-caption text-mute tabular-nums">
                    {photoResults.length} matching {photoResults.length === 1 ? "photo" : "photos"}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                  {photoResults.map((item) => (
                    <article
                      key={item.image_id}
                      className="bg-paper border border-sandstone rounded-none overflow-hidden flex flex-col"
                    >
                      <Link
                        href={`/sites/${item.site_id}`}
                        className="block aspect-video bg-stone overflow-hidden border-b border-sandstone focus-ring"
                        title={`View ${item.name}`}
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={resolveImageUrl(item.url)}
                          alt={item.name}
                          className="w-full h-full object-cover rounded-none hover:scale-105 transition-transform duration-200"
                        />
                      </Link>

                      <div className="p-3.5 space-y-2 flex-1 flex flex-col justify-between">
                        <div>
                          <Link
                            href={`/sites/${item.site_id}`}
                            className="font-serif font-semibold text-ink text-[17px] leading-[22px] hover:text-indigo hover:underline block"
                          >
                            {item.name}
                          </Link>
                          <div className="type-caption text-mute mt-0.5">{item.region}</div>
                          <ResultAttribution item={item} />
                        </div>

                        {/* Raw score & why line from API data */}
                        <div className="pt-2 border-t border-sandstone/40 space-y-1">
                          <div className="flex items-center justify-between text-[13px]">
                            <span className="text-mute">Visual similarity:</span>
                            <span
                              title="Similarity to the query, not a probability."
                              className="font-mono text-xs tabular-nums font-semibold px-2 py-0.5 rounded-[4px] bg-stone text-indigo border border-sandstone/50 cursor-help"
                            >
                              {formatSimilarityScore(item.score)}
                            </span>
                          </div>
                          <div className="type-caption text-mute truncate" title={`Cosine score: ${formatSimilarityScore(item.score)}`}>
                            Score: {formatSimilarityScore(item.score)} visual similarity
                          </div>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
