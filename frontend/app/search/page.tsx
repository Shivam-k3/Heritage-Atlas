import React from "react";
import { Navbar } from "@/components/Navbar";

export const metadata = {
  title: "Search - Heritage Atlas",
  description: "Search heritage sites by description text or photo upload.",
};

export default function SearchPage() {
  return (
    <div className="min-h-screen bg-stone flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-4xl w-full mx-auto p-6 md:p-10 space-y-8">
        <div>
          <h1 className="type-h1 text-indigo">Search</h1>
          <p className="type-body text-mute mt-1">
            Search heritage sites using text descriptions or upload a photo to find visually similar architecture.
          </p>
        </div>

        {/* Search box mock placeholder per DESIGN.md */}
        <div className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-4">
          <div className="flex items-center gap-2 border-b border-sandstone pb-4">
            <button
              type="button"
              className="px-4 py-1.5 rounded-[6px] bg-stone font-semibold text-indigo type-small focus-ring"
            >
              Text search
            </button>
            <button
              type="button"
              className="px-4 py-1.5 rounded-[6px] text-mute hover:text-ink type-small focus-ring"
            >
              Photo search
            </button>
          </div>

          <div className="relative">
            <input
              type="text"
              readOnly
              value=""
              placeholder="Search by architectural features, e.g. carved pillars, stepwell..."
              className="w-full bg-stone/50 border border-sandstone rounded-[6px] px-4 py-3 type-body text-ink placeholder:text-mute focus-ring"
            />
          </div>

          <div className="pt-2 text-mute type-caption">
            Semantic search powered by MiniLM embeddings over field notes and CLIP image rankings.
          </div>
        </div>
      </main>
    </div>
  );
}
