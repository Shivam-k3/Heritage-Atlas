"use client";

// This page fetches data at runtime — disable static prerendering
export const dynamic = "force-dynamic";

import React, { useEffect, useState, use } from "react";

import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { ProvenanceChip } from "@/components/ProvenanceChip";
import { getRelatedSites, getSite, resolveImageUrl } from "@/lib/api";
import type { RelatedSite, SiteDetail, Tag } from "@/lib/types";

export default function SiteDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const siteId = Number(resolvedParams.id);

  const [site, setSite] = useState<SiteDetail | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [related, setRelated] = useState<RelatedSite[]>([]);
  const [isLoadingRelated, setIsLoadingRelated] = useState<boolean>(true);
  const [relatedError, setRelatedError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    async function load() {
      if (Number.isNaN(siteId)) {
        if (!ignore) {
          setError("Invalid site ID. Return to the explore map.");
          setIsLoading(false);
        }
        return;
      }

      try {
        const data = await getSite(siteId);
        if (!ignore) {
          setSite(data);
          setError(null);
          setIsLoading(false);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setError(
            err instanceof Error
              ? err.message
              : `Site #${siteId} could not be loaded.`
          );
          setIsLoading(false);
        }
      }
    }

    void load();

    return () => {
      ignore = true;
    };
  }, [siteId]);

  // Related sites are a secondary section: failure must not hide the site page.
  useEffect(() => {
    let ignore = false;

    async function loadRelated() {
      if (Number.isNaN(siteId)) {
        setIsLoadingRelated(false);
        return;
      }
      setIsLoadingRelated(true);
      setRelatedError(null);
      try {
        const data = await getRelatedSites(siteId, 5);
        if (!ignore) setRelated(data);
      } catch (err: unknown) {
        if (!ignore) {
          setRelatedError(
            err instanceof Error
              ? err.message
              : "Related sites are unavailable."
          );
        }
      } finally {
        if (!ignore) setIsLoadingRelated(false);
      }
    }

    void loadRelated();
    return () => {
      ignore = true;
    };
  }, [siteId]);

  // Group tags into Site Type and Features per DESIGN.md Section 8.3
  const siteTypeTags: Tag[] = [];
  const featureTags: Tag[] = [];

  if (site?.images) {
    site.images.forEach((img) => {
      img.tags.forEach((t) => {
        if (t.tag_type === "site_type") {
          if (!siteTypeTags.some((existing) => existing.id === t.id)) {
            siteTypeTags.push(t);
          }
        } else {
          if (!featureTags.some((existing) => existing.id === t.id)) {
            featureTags.push(t);
          }
        }
      });
    });
  }

  return (
    <div className="min-h-screen bg-stone flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-8 sm:px-6 md:py-10 space-y-8">
        {/* Navigation & breadcrumb */}
        <div className="flex items-center justify-between border-b border-sandstone pb-4">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] border border-sandstone bg-paper text-indigo type-small font-medium hover:bg-stone focus-ring transition-colors"
          >
            <span aria-hidden="true">&larr;</span>
            <span>Back to Explore</span>
          </Link>

          <Link
            href={`/trails?site=${siteId}`}
            className="px-4 py-2 rounded-[6px] bg-paper border border-sandstone text-indigo type-small font-semibold hover:bg-stone focus-ring transition-colors"
          >
            Add to trail
          </Link>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="space-y-6 animate-pulse">
            <div className="h-10 bg-paper/60 rounded-[6px] w-2/3 border border-sandstone/30" />
            <div className="h-5 bg-paper/60 rounded-[6px] w-1/4 border border-sandstone/30" />
            <div className="w-full aspect-video bg-paper/60 rounded-none border border-sandstone/30" />
            <div className="h-28 bg-paper/60 rounded-[6px] border border-sandstone/30" />
          </div>
        )}

        {/* Error State per DESIGN.md */}
        {!isLoading && error && (
          <div className="bg-paper p-8 rounded-[10px] border border-clay-red/40 text-center space-y-4">
            <h2 className="type-h2 text-clay-red">Couldn&apos;t load site</h2>
            <p className="type-body text-ink">{error}</p>
            <div className="pt-2">
              <Link
                href="/"
                className="px-4 py-2 bg-indigo text-paper rounded-[6px] type-small font-semibold focus-ring inline-block"
              >
                Return to Explore map
              </Link>
            </div>
          </div>
        )}

        {/* Site Details Content */}
        {!isLoading && !error && site && (
          <article className="space-y-8">
            {/* Header: Name, Region, Category */}
            <div>
              <h1 className="type-h1 text-indigo font-serif font-semibold">
                {site.name}
              </h1>
              <div className="flex flex-wrap items-center gap-3 mt-2 text-mute type-small">
                <span className="capitalize font-semibold text-ink">
                  {site.category}
                </span>
                <span>&bull;</span>
                <span>{site.region}</span>
                <span>&bull;</span>
                <span className="tabular-nums font-mono text-xs">
                  {typeof site.lat === "number" && typeof site.lon === "number"
                    ? `${site.lat.toFixed(4)}° N, ${site.lon.toFixed(4)}° E`
                    : "Coordinates not recorded"}
                </span>
              </div>
            </div>

            {/* Leading Main Photo per DESIGN.md: radius 0, large lead */}
            {site.images && site.images.length > 0 && (
              <div className="space-y-2">
                <div className="w-full bg-paper border border-sandstone rounded-none overflow-hidden max-h-[520px] flex items-center justify-center">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={resolveImageUrl(site.images[0].url)}
                    alt={site.name}
                    className="w-full h-auto max-h-[520px] object-contain rounded-none"
                  />
                </div>
                <div className="type-caption text-mute flex flex-wrap items-center justify-between px-1">
                  <span>Photo by {site.images[0].author}</span>
                  <span>Licence: {site.images[0].licence}</span>
                </div>
              </div>
            )}

            {/* Original Field Note per DESIGN.md Section 3: 3 px sandstone left rule */}
            <section
              aria-label="Original field notes"
              className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-3"
            >
              <div className="field-note-rule space-y-1">
                <span className="type-caption text-sandstone font-semibold uppercase tracking-wider block">
                  Original field note
                </span>
                <p className="type-body text-ink leading-relaxed">
                  {site.description}
                </p>
                <div className="type-caption text-mute pt-2">
                  Permanent record &bull; AI classification never overwrites field documentation
                </div>
              </div>
            </section>

            {/* Tags grouped into Site type and Features with provenance chips */}
            <section
              aria-label="Site features and tags"
              className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-6"
            >
              <h2 className="type-h2 text-indigo border-b border-sandstone pb-3">
                Architectural tags &amp; provenance
              </h2>

              {/* Site Type tags */}
              <div className="space-y-2">
                <h3 className="type-small font-semibold text-ink">Site type</h3>
                <div className="flex flex-wrap gap-2.5 pt-1">
                  {siteTypeTags.length > 0 ? (
                    siteTypeTags.map((tag) => (
                      <ProvenanceChip
                        key={tag.id}
                        status={tag.status}
                        label={tag.label}
                        score={tag.score}
                      />
                    ))
                  ) : (
                    <span className="type-small text-mute">
                      No site type tags recorded.
                    </span>
                  )}
                </div>
              </div>

              {/* Features tags */}
              <div className="space-y-2 pt-4 border-t border-sandstone/60">
                <h3 className="type-small font-semibold text-ink">Features</h3>
                <div className="flex flex-wrap gap-2.5 pt-1">
                  {featureTags.length > 0 ? (
                    featureTags.map((tag) => (
                      <ProvenanceChip
                        key={tag.id}
                        status={tag.status}
                        label={tag.label}
                        score={tag.score}
                      />
                    ))
                  ) : (
                    <span className="type-small text-mute">
                      No features detected or reviewed yet.
                    </span>
                  )}
                </div>
                <div className="type-caption text-mute pt-1">
                  Scores indicate raw cosine similarity to the label, not a probability percentage.
                </div>
              </div>
            </section>

            {/* Photo Gallery in masonry-style layout keeping native aspect ratio */}
            {site.images && site.images.length > 1 && (
              <section
                aria-label="Photo gallery"
                className="space-y-4 pt-4"
              >
                <h2 className="type-h2 text-indigo">Documentation gallery</h2>
                <div className="columns-1 sm:columns-2 gap-4 space-y-4">
                  {site.images.slice(1).map((img) => (
                    <div
                      key={img.id}
                      className="break-inside-avoid bg-paper border border-sandstone rounded-none overflow-hidden space-y-1.5 p-2"
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={resolveImageUrl(img.url)}
                        alt={`${site.name} architectural detail`}
                        className="w-full h-auto object-cover rounded-none"
                      />
                      <div className="type-caption text-mute px-1">
                        Photo by {img.author} &bull; {img.licence}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Related sites: simple list, failure stays local to this section */}
            <section
              aria-label="Related heritage sites"
              className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-3"
            >
              <h2 className="type-h2 text-indigo border-b border-sandstone pb-3">
                Related sites
              </h2>

              {isLoadingRelated && (
                <p className="type-small text-mute">Loading related sites...</p>
              )}

              {!isLoadingRelated && relatedError && (
                <p className="type-small text-clay-red">
                  Related sites are unavailable: {relatedError}
                </p>
              )}

              {!isLoadingRelated &&
                !relatedError &&
                related.length === 0 && (
                  <p className="type-small text-mute">
                    No related sites are available yet. This needs stored image
                    embeddings and tags.
                  </p>
                )}

              {!isLoadingRelated &&
                !relatedError &&
                related.length > 0 && (
                  <ul className="space-y-2">
                    {related.map((item) => (
                      <li
                        key={item.site_id}
                        className="flex flex-wrap items-center justify-between gap-2 border border-sandstone/70 rounded-[6px] px-3 py-2 bg-stone/30"
                      >
                        <div className="min-w-0">
                          <Link
                            href={`/sites/${item.site_id}`}
                            className="type-small font-semibold text-indigo hover:underline break-words"
                          >
                            {item.name}
                          </Link>
                          <div className="type-caption text-mute">
                            {item.shared_tags.length > 0
                              ? `Shared tags: ${item.shared_tags.join(", ")}`
                              : "No shared verified tags"}
                          </div>
                        </div>
                        <span
                          title="Combined similarity, not a probability."
                          className="font-mono text-xs tabular-nums font-semibold px-2 py-0.5 rounded-[4px] bg-stone text-indigo border border-sandstone/50 shrink-0"
                        >
                          {item.score.toFixed(2)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
            </section>
          </article>
        )}
      </main>
    </div>
  );
}
