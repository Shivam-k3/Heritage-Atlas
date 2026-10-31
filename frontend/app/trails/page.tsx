import React from "react";
import { Navbar } from "@/components/Navbar";

export const metadata = {
  title: "Trails - Heritage Atlas",
  description: "Curated cultural journeys and stepped routes.",
};

export default function TrailsPage() {
  return (
    <div className="min-h-screen bg-stone flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-4xl w-full mx-auto p-6 md:p-10 space-y-8">
        <div>
          <h1 className="type-h1 text-indigo">Explorer trails</h1>
          <p className="type-body text-mute mt-1">
            Follow journeys across stone architecture. Stops are organized as descending steps with haversine distances.
          </p>
        </div>

        {/* Stepped route preview card */}
        <div className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-4">
          <div className="border-b border-sandstone pb-3 flex items-center justify-between">
            <div>
              <h2 className="type-h2 text-indigo">Gujarat Stepwell Trail</h2>
              <span className="type-caption text-mute">3 stops &bull; 108.4 km total</span>
            </div>
            <button
              type="button"
              className="px-4 py-2 bg-indigo text-paper rounded-[6px] type-small font-semibold focus-ring hover:bg-indigo/90"
            >
              Open trail
            </button>
          </div>

          {/* Stepped visualization mockup per DESIGN.md Section 2 */}
          <div className="py-4 space-y-3">
            <div className="flex items-center gap-4">
              <span className="w-6 h-6 rounded-full bg-indigo text-paper text-xs flex items-center justify-center font-mono">1</span>
              <div>
                <div className="type-small font-semibold text-ink">Adalaj Stepwell</div>
                <div className="type-caption text-mute">Gandhinagar, Gujarat</div>
              </div>
            </div>

            <div className="ml-3 pl-6 border-l-2 border-sandstone py-2">
              <span className="type-caption text-mute bg-stone px-2 py-0.5 rounded-[4px] tabular-nums font-mono">
                &darr; 84.2 km
              </span>
            </div>

            <div className="flex items-center gap-4">
              <span className="w-6 h-6 rounded-full bg-indigo text-paper text-xs flex items-center justify-center font-mono">2</span>
              <div>
                <div className="type-small font-semibold text-ink">Sun Temple, Modhera</div>
                <div className="type-caption text-mute">Modhera, Gujarat</div>
              </div>
            </div>

            <div className="ml-3 pl-6 border-l-2 border-sandstone py-2">
              <span className="type-caption text-mute bg-stone px-2 py-0.5 rounded-[4px] tabular-nums font-mono">
                &darr; 34.6 km
              </span>
            </div>

            <div className="flex items-center gap-4">
              <span className="w-6 h-6 rounded-full bg-indigo text-paper text-xs flex items-center justify-center font-mono">3</span>
              <div>
                <div className="type-small font-semibold text-ink">Rani ki Vav</div>
                <div className="type-caption text-mute">Patan, Gujarat</div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
