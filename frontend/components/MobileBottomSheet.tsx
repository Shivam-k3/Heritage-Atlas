"use client";

import React, { useState } from "react";

export type SheetSnap = "peek" | "half" | "full";

export interface MobileBottomSheetProps {
  children: React.ReactNode;
  selectedSiteName?: string | null;
  siteCount: number;
}

export const MobileBottomSheet: React.FC<MobileBottomSheetProps> = ({
  children,
  selectedSiteName,
  siteCount,
}) => {
  const [snap, setSnap] = useState<SheetSnap>("peek");

  function cycleSnap() {
    if (snap === "peek") setSnap("half");
    else if (snap === "half") setSnap("full");
    else setSnap("peek");
  }

  function getSnapClasses(): string {
    switch (snap) {
      case "peek":
        return "h-20";
      case "half":
        return "h-[48vh]";
      case "full":
        return "h-[86vh]";
    }
  }

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 z-40 bg-paper border-t border-sandstone shadow-[0_-4px_16px_rgba(26,29,38,0.15)] flex flex-col transition-all duration-300 ease-in-out md:hidden ${getSnapClasses()}`}
    >
      {/* Drag handle & header bar */}
      <button
        type="button"
        onClick={cycleSnap}
        aria-label={`Toggle bottom sheet, current state: ${snap}`}
        className="w-full shrink-0 flex flex-col items-center pt-2 pb-1.5 px-4 bg-paper hover:bg-stone/40 border-b border-sandstone/40 focus-ring cursor-pointer"
      >
        {/* Grab pill */}
        <div className="w-10 h-1 rounded-full bg-sandstone/70 mb-2" />

        {/* Peek summary bar */}
        <div className="w-full flex items-center justify-between text-left">
          <div className="min-w-0 pr-2">
            {selectedSiteName ? (
              <div className="font-serif font-semibold text-indigo text-sm truncate">
                {selectedSiteName}
              </div>
            ) : (
              <div className="font-sans font-semibold text-ink text-sm">
                Explore heritage sites{" "}
                <span className="text-mute font-normal">({siteCount})</span>
              </div>
            )}
          </div>
          <div className="shrink-0 text-mute type-caption font-medium capitalize bg-stone px-2 py-0.5 rounded-[4px]">
            {snap} &bull; {snap === "full" ? "collapse" : "expand"}
          </div>
        </div>
      </button>

      {/* Sheet scrollable content */}
      <div className="flex-1 overflow-hidden relative">
        {children}
      </div>
    </div>
  );
};
