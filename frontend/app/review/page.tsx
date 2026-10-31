import React from "react";
import { Navbar } from "@/components/Navbar";
import { ProvenanceChip } from "@/components/ProvenanceChip";

export const metadata = {
  title: "Review - Heritage Atlas",
  description: "Human verification queue for AI-suggested heritage tags.",
};

export default function ReviewPage() {
  return (
    <div className="min-h-screen bg-stone flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-4xl w-full mx-auto p-6 md:p-10 space-y-8">
        <div>
          <h1 className="type-h1 text-indigo">Review queue</h1>
          <p className="type-body text-mute mt-1">
            Human verification queue sorted by lowest similarity score first. Decisions are append-only.
          </p>
        </div>

        <div className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-6">
          <div className="border-b border-sandstone pb-4 flex items-center justify-between">
            <div>
              <span className="type-caption text-mute">Item 1 of 12</span>
              <h2 className="type-h2 text-indigo mt-0.5">Rani ki Vav &bull; Tag verification</h2>
            </div>
            <ProvenanceChip status="suggested" score={0.27} />
          </div>

          <div className="space-y-4">
            <div className="type-body text-ink">
              Suggested tag: <span className="font-semibold">carved pillars</span>
            </div>
            <div className="type-caption text-mute">
              Raw cosine similarity: 0.27. AI suggestions never overwrite original field records.
            </div>

            <div className="flex flex-wrap gap-3 pt-2">
              <button
                type="button"
                className="px-4 py-2 bg-water text-paper rounded-[6px] type-small font-semibold focus-ring hover:bg-water/90"
              >
                Confirm
              </button>
              <button
                type="button"
                className="px-4 py-2 bg-paper text-clay-red border border-clay-red/40 rounded-[6px] type-small font-semibold focus-ring hover:bg-clay-red/5"
              >
                Reject
              </button>
              <button
                type="button"
                className="px-4 py-2 bg-stone text-ink border border-sandstone rounded-[6px] type-small font-semibold focus-ring hover:bg-paper"
              >
                Add tag
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
