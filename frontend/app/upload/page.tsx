"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { getSites, uploadImage, getJob } from "@/lib/api";
import type { SiteSummary } from "@/lib/types";

// Dynamic import for Leaflet location picker map (SSR disabled)
const LocationPickerMap = dynamic(() => import("@/components/LocationPickerMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-56 bg-stone flex items-center justify-center text-mute type-caption border border-sandstone rounded-[6px]">
      Loading map for location selection...
    </div>
  ),
});

export type UploadItemStatus =
  | "queued"
  | "uploading"
  | "uploaded"
  | "analysing"
  | "done"
  | "failed";

export interface PhotoUploadProgress {
  id: string;
  file: File;
  previewUrl: string;
  status: UploadItemStatus;
  jobId?: number;
  siteId?: number;
  error?: string;
}

export default function UploadPage() {
  const [existingSites, setExistingSites] = useState<SiteSummary[]>([]);
  const [isLoadingSites, setIsLoadingSites] = useState<boolean>(true);

  // Form inputs
  const [files, setFiles] = useState<File[]>([]);
  const [siteMode, setSiteMode] = useState<"existing" | "new">("existing");
  const [selectedSiteId, setSelectedSiteId] = useState<string>("");
  const [newSiteName, setNewSiteName] = useState<string>("");
  const [author, setAuthor] = useState<string>("");
  const [licence, setLicence] = useState<string>("CC BY-SA 4.0");
  const [lat, setLat] = useState<number | null>(23.8593);
  const [lon, setLon] = useState<number | null>(72.1018);
  const [description, setDescription] = useState<string>("");

  // Upload progress & states
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [uploadQueue, setUploadQueue] = useState<PhotoUploadProgress[]>([]);
  const [globalMessage, setGlobalMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load existing sites for site picker
  useEffect(() => {
    let ignore = false;
    getSites()
      .then((data) => {
        if (!ignore) {
          setExistingSites(data);
          if (data.length > 0) {
            setSelectedSiteId(String(data[0].id));
          }
          setIsLoadingSites(false);
        }
      })
      .catch(() => {
        if (!ignore) setIsLoadingSites(false);
      });

    return () => {
      ignore = true;
    };
  }, []);

  const handleFilesAdded = (newFiles: FileList | null) => {
    if (!newFiles) return;
    const added: File[] = [];
    for (let i = 0; i < newFiles.length; i++) {
      const f = newFiles[i];
      if (f.type.startsWith("image/")) {
        added.push(f);
      }
    }
    setFiles((prev) => [...prev, ...added]);
    setFormError(null);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // Poll /jobs/{id} every 2 seconds per Task 7
  const pollJobStatus = async (jobId: number): Promise<"done" | "failed"> => {
    const maxPolls = 30; // 60 seconds maximum
    for (let attempt = 0; attempt < maxPolls; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      try {
        const job = await getJob(jobId);
        if (job.status === "done") {
          return "done";
        }
        if (job.status === "failed") {
          return "failed";
        }
      } catch {
        // Continue polling if transient failure
      }
    }
    return "done"; // Fallback after timeout
  };

  // Sequential upload handler: uploads one photo at a time per Task 7
  const handleUploadSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setFormError(null);
      setGlobalMessage(null);

      // Validation
      if (files.length === 0) {
        setFormError("Please select at least one photo to upload.");
        return;
      }
      if (siteMode === "existing" && !selectedSiteId) {
        setFormError("Please pick an existing site or select 'New site'.");
        return;
      }
      if (siteMode === "new" && !newSiteName.trim()) {
        setFormError("Please enter a name for the new site.");
        return;
      }
      if (!author.trim()) {
        setFormError("Author is required for heritage documentation.");
        return;
      }
      if (!licence.trim()) {
        setFormError("Licence is required.");
        return;
      }

      setIsSubmitting(true);
      setGlobalMessage("Photo uploaded. Analysing now.");

      // Initialize queue
      const initialQueue: PhotoUploadProgress[] = files.map((f, idx) => ({
        id: `${f.name}-${idx}-${Date.now()}`,
        file: f,
        previewUrl: URL.createObjectURL(f),
        status: "queued",
      }));
      setUploadQueue(initialQueue);

      // Process one at a time per Task 7
      for (let i = 0; i < initialQueue.length; i++) {
        const item = initialQueue[i];

        // Update status to uploading
        setUploadQueue((prev) =>
          prev.map((q) => (q.id === item.id ? { ...q, status: "uploading" } : q))
        );

        const formData = new FormData();
        formData.append("file", item.file);
        if (siteMode === "existing") {
          formData.append("site_id", selectedSiteId);
        } else {
          formData.append("site_name", newSiteName.trim());
        }
        formData.append("author", author.trim());
        formData.append("licence", licence.trim());
        if (lat !== null) formData.append("lat", String(lat));
        if (lon !== null) formData.append("lon", String(lon));
        if (description.trim()) formData.append("description", description.trim());

        try {
          // POST /images/upload
          const uploadRes = await uploadImage(formData);

          // Update status to Analysing and record jobId & siteId
          setUploadQueue((prev) =>
            prev.map((q) =>
              q.id === item.id
                ? {
                    ...q,
                    status: "analysing",
                    jobId: uploadRes.job_id,
                    siteId: uploadRes.site_id,
                  }
                : q
            )
          );

          // Poll /jobs/{id} every 2 s until done or failed
          const pollResult = await pollJobStatus(uploadRes.job_id);

          setUploadQueue((prev) =>
            prev.map((q) =>
              q.id === item.id
                ? {
                    ...q,
                    status: pollResult === "done" ? "done" : "failed",
                    error:
                      pollResult === "failed"
                        ? "Feature analysis could not complete."
                        : undefined,
                  }
                : q
            )
          );
        } catch (err: unknown) {
          setUploadQueue((prev) =>
            prev.map((q) =>
              q.id === item.id
                ? {
                    ...q,
                    status: "failed",
                    error:
                      err instanceof Error
                        ? err.message
                        : "Upload failed. Check your connection or try again.",
                  }
                : q
            )
          );
        }
      }

      setIsSubmitting(false);
    },
    [
      files,
      siteMode,
      selectedSiteId,
      newSiteName,
      author,
      licence,
      lat,
      lon,
      description,
    ]
  );

  return (
    <div className="min-h-screen bg-stone flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8 sm:px-6 md:py-10 space-y-8">
        <div>
          <h1 className="type-h1 text-indigo font-serif font-semibold">Upload photo</h1>
          <p className="type-body text-mute mt-1">
            Submit field photography, site notes, and location coordinates. Analysis runs asynchronously.
          </p>
        </div>

        {/* Global confirmation or error banner per DESIGN.md */}
        {globalMessage && (
          <div className="bg-water/10 border border-water text-water p-4 rounded-[6px] type-small font-medium flex items-center justify-between">
            <span>{globalMessage}</span>
            <button
              type="button"
              onClick={() => setGlobalMessage(null)}
              className="text-water text-lg leading-none"
            >
              &times;
            </button>
          </div>
        )}

        {formError && (
          <div className="bg-clay-red/10 border border-clay-red text-clay-red p-4 rounded-[6px] type-small font-semibold">
            {formError}
          </div>
        )}

        {/* Upload Form */}
        <form onSubmit={handleUploadSubmit} className="space-y-8">
          {/* 1. Photos Section */}
          <section className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-4">
            <h2 className="type-h2 text-indigo border-b border-sandstone pb-3">
              1. Field photos (required)
            </h2>

            {/* Dropzone */}
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-sandstone hover:border-indigo rounded-[6px] p-8 text-center space-y-2 bg-stone/20 hover:bg-stone/40 cursor-pointer transition-colors focus-ring"
              tabIndex={0}
              role="button"
              aria-label="Select field photos"
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  fileInputRef.current?.click();
                }
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/*"
                onChange={(e) => handleFilesAdded(e.target.files)}
                className="hidden"
              />
              <svg
                className="w-10 h-10 text-sandstone mx-auto"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <polyline points="21 15 16 10 5 21" />
              </svg>
              <div className="type-small font-semibold text-ink">
                Click or drag photographs to attach
              </div>
              <div className="type-caption text-mute">
                Supports multiple photos. Each image is processed sequentially.
              </div>
            </div>

            {/* Selected files preview */}
            {files.length > 0 && (
              <div className="space-y-2 pt-2">
                <span className="type-caption font-semibold text-ink block">
                  Selected photos ({files.length}):
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {files.map((file, idx) => (
                    <div
                      key={idx}
                      className="relative bg-stone p-2 rounded-[6px] border border-sandstone flex items-center justify-between"
                    >
                      <span className="type-caption text-ink truncate mr-2 font-mono">
                        {file.name}
                      </span>
                      <button
                        type="button"
                        onClick={() => removeFile(idx)}
                        aria-label={`Remove ${file.name}`}
                        className="text-mute hover:text-clay-red font-bold text-sm px-1"
                      >
                        &times;
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* 2. Site Association */}
          <section className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-4">
            <h2 className="type-h2 text-indigo border-b border-sandstone pb-3">
              2. Heritage site (required)
            </h2>

            <div className="flex gap-4">
              <label className="inline-flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="siteMode"
                  checked={siteMode === "existing"}
                  onChange={() => setSiteMode("existing")}
                  className="text-indigo focus-ring"
                />
                <span className="type-small font-semibold text-ink">
                  Existing site
                </span>
              </label>

              <label className="inline-flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="siteMode"
                  checked={siteMode === "new"}
                  onChange={() => setSiteMode("new")}
                  className="text-indigo focus-ring"
                />
                <span className="type-small font-semibold text-ink">
                  New site
                </span>
              </label>
            </div>

            {siteMode === "existing" ? (
              <div className="space-y-1">
                <label
                  htmlFor="upload-existing-site"
                  className="type-caption text-mute block"
                >
                  Pick from documented sites:
                </label>
                {isLoadingSites ? (
                  <div className="type-caption text-mute">Loading sites list...</div>
                ) : (
                  <select
                    id="upload-existing-site"
                    value={selectedSiteId}
                    onChange={(e) => setSelectedSiteId(e.target.value)}
                    className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3.5 py-2.5 type-small text-ink focus-ring"
                  >
                    {existingSites.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.region} &bull; {s.category})
                      </option>
                    ))}
                  </select>
                )}
              </div>
            ) : (
              <div className="space-y-1">
                <label
                  htmlFor="upload-new-site"
                  className="type-caption text-mute block"
                >
                  New heritage site name:
                </label>
                <input
                  id="upload-new-site"
                  type="text"
                  value={newSiteName}
                  onChange={(e) => setNewSiteName(e.target.value)}
                  placeholder="E.g. Nagda Sas-Bahu Temples"
                  className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3.5 py-2.5 type-body text-ink placeholder:text-mute focus-ring"
                />
              </div>
            )}
          </section>

          {/* 3. Attribution & Licence */}
          <section className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-4">
            <h2 className="type-h2 text-indigo border-b border-sandstone pb-3">
              3. Author &amp; licence (required)
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label
                  htmlFor="upload-author"
                  className="type-caption font-semibold text-ink block"
                >
                  Photographer / Author:
                </label>
                <input
                  id="upload-author"
                  type="text"
                  value={author}
                  onChange={(e) => setAuthor(e.target.value)}
                  placeholder="E.g. Dr. K. Mehta"
                  className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3.5 py-2.5 type-body text-ink placeholder:text-mute focus-ring"
                  required
                />
              </div>

              <div className="space-y-1">
                <label
                  htmlFor="upload-licence"
                  className="type-caption font-semibold text-ink block"
                >
                  Open licence:
                </label>
                <select
                  id="upload-licence"
                  value={licence}
                  onChange={(e) => setLicence(e.target.value)}
                  className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3.5 py-2.5 type-small text-ink focus-ring"
                  required
                >
                  <option value="CC BY-SA 4.0">CC BY-SA 4.0 (ShareAlike)</option>
                  <option value="CC BY 4.0">CC BY 4.0 (Attribution)</option>
                  <option value="CC0 1.0">CC0 (Public Domain)</option>
                  <option value="All rights reserved - Research archive only">
                    Archive use only
                  </option>
                </select>
              </div>
            </div>
          </section>

          {/* 4. Location: Click on Map + Manual Lat/Lon */}
          <section className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-4">
            <h2 className="type-h2 text-indigo border-b border-sandstone pb-3">
              4. Geographic location
            </h2>

            <p className="type-caption text-mute">
              Couldn&apos;t read GPS from this photo. Click the map to set the location.
            </p>

            <LocationPickerMap
              lat={lat}
              lon={lon}
              onChange={(newLat, newLon) => {
                setLat(newLat);
                setLon(newLon);
              }}
            />

            <div className="grid grid-cols-2 gap-4 pt-1">
              <div>
                <label
                  htmlFor="upload-lat"
                  className="type-caption font-medium text-ink block"
                >
                  Latitude (° N):
                </label>
                <input
                  id="upload-lat"
                  type="number"
                  step="0.0001"
                  value={lat ?? ""}
                  onChange={(e) =>
                    setLat(e.target.value ? parseFloat(e.target.value) : null)
                  }
                  className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3 py-2 type-small text-ink font-mono tabular-nums focus-ring"
                />
              </div>

              <div>
                <label
                  htmlFor="upload-lon"
                  className="type-caption font-medium text-ink block"
                >
                  Longitude (° E):
                </label>
                <input
                  id="upload-lon"
                  type="number"
                  step="0.0001"
                  value={lon ?? ""}
                  onChange={(e) =>
                    setLon(e.target.value ? parseFloat(e.target.value) : null)
                  }
                  className="w-full bg-stone/40 border border-sandstone rounded-[6px] px-3 py-2 type-small text-ink font-mono tabular-nums focus-ring"
                />
              </div>
            </div>
          </section>

          {/* 5. Original Field Notes (Optional) */}
          <section className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-3">
            <h2 className="type-h2 text-indigo border-b border-sandstone pb-3">
              5. Field documentation note (optional)
            </h2>
            <div className="field-note-rule space-y-1">
              <span className="type-caption text-sandstone font-semibold block">
                Field note
              </span>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                placeholder="Architectural observations, inscription notes, conservation state..."
                className="w-full bg-stone/30 border border-sandstone rounded-[6px] p-3 type-body text-ink placeholder:text-mute focus-ring"
              />
            </div>
          </section>

          {/* Submit button per DESIGN.md Section 11: "Upload photo" */}
          <div className="pt-2">
            <button
              type="submit"
              disabled={isSubmitting || files.length === 0}
              className="w-full sm:w-auto px-8 py-3 bg-indigo text-paper rounded-[6px] type-body font-semibold focus-ring hover:bg-indigo/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting
                ? "Uploading..."
                : files.length > 1
                ? "Upload photos"
                : "Upload photo"}
            </button>
          </div>
        </form>

        {/* Upload & Analysis Progress List per Task 7 */}
        {uploadQueue.length > 0 && (
          <section
            aria-label="Upload progress"
            className="bg-paper p-6 rounded-[10px] border border-sandstone space-y-4"
          >
            <h2 className="type-h2 text-indigo border-b border-sandstone pb-2">
              Upload &amp; analysis progress
            </h2>

            <div className="space-y-3">
              {uploadQueue.map((item) => (
                <div
                  key={item.id}
                  className="p-3.5 bg-stone/40 border border-sandstone rounded-[6px] flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-12 h-12 bg-stone border border-sandstone rounded-none overflow-hidden shrink-0">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={item.previewUrl}
                        alt={item.file.name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="min-w-0">
                      <div className="type-small font-semibold text-ink truncate">
                        {item.file.name}
                      </div>
                      <div className="type-caption text-mute">
                        {(item.file.size / 1024).toFixed(0)} KB
                      </div>
                    </div>
                  </div>

                  {/* Status Badges per Task 7: Uploaded, Analysing, Ready to review */}
                  <div className="flex items-center gap-3 shrink-0">
                    {item.status === "queued" && (
                      <span className="type-caption text-mute px-2.5 py-1 rounded-[4px] bg-stone border border-sandstone/60">
                        Queued
                      </span>
                    )}
                    {item.status === "uploading" && (
                      <span className="type-caption text-indigo font-semibold px-2.5 py-1 rounded-[4px] bg-stone border border-indigo/40 animate-pulse">
                        Uploading...
                      </span>
                    )}
                    {item.status === "uploaded" && (
                      <span className="type-caption text-water font-semibold px-2.5 py-1 rounded-[4px] bg-water/10 border border-water/40">
                        Uploaded
                      </span>
                    )}
                    {item.status === "analysing" && (
                      <span className="type-caption text-turmeric font-semibold px-2.5 py-1 rounded-[4px] bg-turmeric/10 border border-turmeric/40 flex items-center gap-1.5 animate-pulse">
                        <span className="w-2 h-2 rounded-full bg-turmeric animate-ping" />
                        Analysing
                      </span>
                    )}
                    {item.status === "done" && (
                      <div className="flex items-center gap-2">
                        <span className="type-caption text-water font-semibold px-2.5 py-1 rounded-[4px] bg-water text-paper">
                          Ready to review
                        </span>
                        {item.siteId && (
                          <Link
                            href={`/sites/${item.siteId}`}
                            className="type-caption text-indigo font-semibold underline hover:text-indigo/80 focus-ring"
                          >
                            View site &rarr;
                          </Link>
                        )}
                      </div>
                    )}
                    {item.status === "failed" && (
                      <span className="type-caption text-clay-red font-semibold px-2.5 py-1 rounded-[4px] bg-clay-red/10 border border-clay-red/40">
                        {item.error || "Failed"}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
