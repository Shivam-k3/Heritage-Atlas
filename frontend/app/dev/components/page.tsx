"use client";

import React from "react";
import Link from "next/link";
import { ProvenanceChip } from "@/components/ProvenanceChip";


export default function DevComponentsPage() {
  return (
    <main className="min-h-screen bg-stone text-ink p-6 md:p-12">
      <div className="max-w-4xl mx-auto space-y-10">
        {/* Navigation back */}
        <div className="flex items-center justify-between border-b border-sandstone pb-4">
          <div>
            <h1 className="type-h1 text-indigo">Design system showcase</h1>
            <p className="type-small text-mute mt-1">
              Internal verification for provenance layers, tokens, and UI states per DESIGN.md
            </p>
          </div>
          <Link
            href="/"
            className="px-4 py-2 bg-paper text-indigo border border-sandstone rounded-[6px] type-small font-semibold focus-ring hover:bg-stone transition-colors"
          >
            Back to Explore
          </Link>
        </div>

        {/* 1. Provenance Chips Section */}
        <section className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-6">
          <div className="border-b border-sandstone pb-3">
            <h2 className="type-h2 text-indigo">1. Provenance chips</h2>
            <p className="type-small text-mute mt-1">
              Every piece of information distinguishes its provenance layer. Never rely on colour alone.
            </p>
          </div>

          {/* Standalone Chips */}
          <div className="space-y-3">
            <h3 className="type-h3 text-ink">Standalone provenance badges</h3>
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <ProvenanceChip status="suggested" />
              <ProvenanceChip status="verified" />
              <ProvenanceChip status="added" />
              <ProvenanceChip status="rejected" />
            </div>
            <p className="type-caption text-mute">
              Shapes: Suggested has dashed 1.5 px amber outline with sparkle; Verified has solid teal with check;
              Added has solid 1.5 px teal outline with person icon; Rejected has strikethrough and slash icon.
            </p>
          </div>

          {/* Tag Chips with labels and scores */}
          <div className="space-y-3 pt-4 border-t border-sandstone">
            <h3 className="type-h3 text-ink">Tag chips with cosine similarity scores</h3>
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <ProvenanceChip
                status="suggested"
                label="carved pillars"
                score={0.27}
              />
              <ProvenanceChip
                status="verified"
                label="stepwell"
                score={0.94}
              />
              <ProvenanceChip
                status="added"
                label="stepped pavilion"
                score={0.71}
              />
              <ProvenanceChip
                status="rejected"
                label="stringcourse frieze"
                score={0.58}
              />
            </div>
            <p className="type-caption text-mute">
              Hover over score badges to see tooltip: &ldquo;Similarity to the label, not a probability.&rdquo;
            </p>
          </div>

          {/* Interactive States */}
          <div className="space-y-3 pt-4 border-t border-sandstone">
            <h3 className="type-h3 text-ink">Interactive &amp; disabled states (keyboard focusable)</h3>
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <ProvenanceChip
                status="suggested"
                label="Interactive suggested"
                interactive
                onClick={() => alert("Suggested chip clicked")}
              />
              <ProvenanceChip
                status="verified"
                label="Interactive verified"
                interactive
                onClick={() => alert("Verified chip clicked")}
              />
              <ProvenanceChip
                status="added"
                label="Disabled added"
                interactive
                disabled
              />
              <ProvenanceChip
                status="rejected"
                label="Disabled rejected"
                interactive
                disabled
              />
            </div>
            <p className="type-caption text-mute">
              Tab into the buttons above to inspect the 2 px indigo focus ring with 2 px offset.
            </p>
          </div>
        </section>

        {/* 2. Original Source / Field Note Bar */}
        <section className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-6">
          <div className="border-b border-sandstone pb-3">
            <h2 className="type-h2 text-indigo">2. Original source &amp; field notes</h2>
            <p className="type-small text-mute mt-1">
              Field notes sit under a 3 px sandstone left rule. Plain text, never overwritten by AI output.
            </p>
          </div>

          <div className="field-note-rule space-y-1">
            <span className="type-caption text-sandstone font-semibold">Field note</span>
            <p className="type-body text-ink">
              Subterranean stepwell in Patan built in the 11th century by Queen Udayamati. Designed as an inverted temple honoring water sanctity with seven pillared terraces and over five hundred principal sculptures.
            </p>
            <span className="type-caption text-mute block mt-2">
              Photo and note by Dr. K. Mehta &bull; Licence: CC BY-SA 4.0
            </span>
          </div>
        </section>

        {/* 3. Colour & Radii Tokens */}
        <section className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-6">
          <div className="border-b border-sandstone pb-3">
            <h2 className="type-h2 text-indigo">3. Design tokens</h2>
            <p className="type-small text-mute mt-1">
              Strict tokens from DESIGN.md. No raw hex in components.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <div className="p-3 bg-stone border border-sandstone rounded-[6px]">
              <div className="type-small font-semibold text-ink">--stone</div>
              <div className="type-caption text-mute">Page background</div>
            </div>
            <div className="p-3 bg-paper border border-sandstone rounded-[6px]">
              <div className="type-small font-semibold text-ink">--paper</div>
              <div className="type-caption text-mute">Panels &amp; inputs</div>
            </div>
            <div className="p-3 bg-indigo text-paper rounded-[6px]">
              <div className="type-small font-semibold">--indigo</div>
              <div className="type-caption opacity-80">Headings &amp; actions</div>
            </div>
            <div className="p-3 bg-sandstone text-paper rounded-[6px]">
              <div className="type-small font-semibold">--sandstone</div>
              <div className="type-caption opacity-90">Borders &amp; rules</div>
            </div>
            <div className="p-3 bg-water text-paper rounded-[6px]">
              <div className="type-small font-semibold">--water</div>
              <div className="type-caption opacity-90">Verified &amp; success</div>
            </div>
            <div className="p-3 border border-turmeric text-turmeric rounded-[6px]">
              <div className="type-small font-semibold">--turmeric</div>
              <div className="type-caption text-mute">AI-suggested</div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
