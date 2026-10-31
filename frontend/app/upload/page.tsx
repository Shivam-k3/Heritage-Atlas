import React from "react";
import { Navbar } from "@/components/Navbar";

export const metadata = {
  title: "Upload - Heritage Atlas",
  description: "Upload field photos, notes, and coordinates.",
};

export default function UploadPage() {
  return (
    <div className="min-h-screen bg-stone flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-4xl w-full mx-auto p-6 md:p-10 space-y-8">
        <div>
          <h1 className="type-h1 text-indigo">Upload photo</h1>
          <p className="type-body text-mute mt-1">
            Submit field photography and field notes. Images undergo asynchronous CLIP feature analysis.
          </p>
        </div>

        <div className="bg-paper p-8 rounded-[10px] border border-sandstone space-y-6">
          {/* Dropzone mock */}
          <div className="border-2 border-dashed border-sandstone rounded-[6px] p-10 text-center space-y-3 bg-stone/30">
            <svg
              className="w-10 h-10 text-sandstone mx-auto"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
            <div className="type-small font-semibold text-ink">
              Drag and drop field photos, or select from device
            </div>
            <div className="type-caption text-mute">
              Supports JPEG and PNG. EXIF metadata will be scanned for GPS coordinates.
            </div>
          </div>

          <div className="type-caption text-mute">
            Upload returns immediately while feature classification runs in the worker queue.
          </div>
        </div>
      </main>
    </div>
  );
}
