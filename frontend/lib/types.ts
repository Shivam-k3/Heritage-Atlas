/**
 * API types matching docs/API.md for Heritage Atlas
 */

export type SiteCategory = "stepwell" | "fort" | "temple" | string;

export type TagType = "site_type" | "feature";

export type TagStatus = "auto" | "verified" | "rejected" | "added_by_human";

export interface Tag {
  id: number;
  label: string;
  tag_type: TagType;
  score: number | null;
  status: TagStatus;
  model_name?: string | null;
  model_version?: string | null;
  prompt_version?: string | null;
}

export interface SiteImage {
  id: number;
  site_id?: number;
  site_name?: string | null;
  url: string;
  original_filename?: string | null;
  author: string;
  licence: string;
  licence_url?: string | null;
  source_url?: string | null;
  status: string;
  tags: Tag[];
}

export interface SiteSummary {
  id: number;
  name: string;
  region: string;
  category: SiteCategory;
  lat: number;
  lon: number;
}

export interface SiteDetail extends SiteSummary {
  description: string;
  images: SiteImage[];
}

export interface GetSitesParams {
  region?: string;
  category?: string;
  tag?: string;
  verified_only?: boolean;
}

export interface UploadResponse {
  site_id: number;
  image_id: number;
  job_id: number | null;
  status: "queued" | string;
  duplicate: boolean;
  url: string;
}

export type JobStatus = "pending" | "running" | "done" | "failed";

export interface JobStatusResponse {
  id: number;
  status: JobStatus;
  error: string | null;
}

export interface TextSearchResult {
  id: number;
  name: string;
  region: string;
  description: string;
  score: number;
}

export interface ImageSearchResult {
  image_id: number;
  site_id: number;
  name: string;
  region: string;
  category?: string | null;
  url: string;
  score: number;
  author?: string | null;
  licence?: string | null;
  licence_url?: string | null;
  source_url?: string | null;
  tags?: Tag[];
}

export interface ReviewQueueItem {
  id: number;
  image_id: number;
  site_id: number;
  site_name: string;
  label: string;
  tag_type: TagType;
  score: number | null;
  status: TagStatus;
  created_at: string;
  url: string;
  author?: string | null;
  licence?: string | null;
  licence_url?: string | null;
  source_url?: string | null;
  model_name?: string | null;
  model_version?: string | null;
  prompt_version?: string | null;
}

export interface ReviewHistoryEntry {
  id: number;
  image_tag_id: number;
  reviewer: string;
  reviewer_id?: number | null;
  action: string;
  previous_status?: string | null;
  new_status?: string | null;
  created_at: string;
}

export interface ReviewTagResponse {
  id: number;
  status: TagStatus;
  previous_status?: TagStatus | null;
  new_status: TagStatus;
}

export interface AddTagResponse extends ReviewTagResponse {
  status: "added_by_human";
}

export interface RelatedSite {
  site_id: number;
  name: string;
  score: number;
  clip_similarity: number;
  tag_overlap: number;
  shared_tags: string[];
  evidence: Record<string, number | null>;
}

export interface TrailStop {
  id: number;
  site_id: number;
  site_name: string;
  region?: string | null;
  category?: string | null;
  lat?: number | null;
  lon?: number | null;
  stop_order: number;
  visit_date?: string | null;
  note?: string | null;
}

export interface Trail {
  id: number;
  title: string;
  description?: string | null;
  created_by?: string | null;
  is_public: boolean;
  created_at: string;
  stops: TrailStop[];
}

export interface CreateTrailInput {
  title: string;
  description?: string | null;
  created_by?: string | null;
  is_public?: boolean;
}

export interface UpdateTrailInput {
  title?: string;
  description?: string | null;
  is_public?: boolean;
}

export interface AddTrailStopInput {
  site_id: number;
  visit_date?: string | null;
  note?: string | null;
}

export interface TrailFromImagesInput extends CreateTrailInput {
  image_ids?: number[] | null;
}

export interface TrailFromImagesResult {
  trail: Trail;
  images_used: number;
  images_skipped: number;
}

export interface TrailSummaryLeg {
  from: number;
  to: number;
  km: number;
}

export interface TrailSummary {
  trail_id: number;
  title: string;
  sites: number;
  photos: number;
  total_km: number;
  distance_mode: "straight_line";
  missing_coordinates: number[];
  top_features: string[];
  legs: TrailSummaryLeg[];
}

export interface TrailJournalEntry {
  stop_order: number;
  site_id: number;
  site_name: string;
  visit_date?: string | null;
  original_note?: string | null;
  generated_summary: string;
  generated: boolean;
  photos: number;
  verified_features: string[];
}

export interface TrailJournal {
  trail_id: number;
  title: string;
  generated: boolean;
  entries: TrailJournalEntry[];
}

export interface AIChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AISource {
  kind: "site" | "image";
  label: string;
  site_id?: number | null;
  image_id?: number | null;
  source_url?: string | null;
  licence_url?: string | null;
}

export interface AIChatResponse {
  response: string;
  intent: string;
  sites: SiteSummary[];
  images: ImageSearchResult[];
  sources: AISource[];
  ai_generated: boolean;
  warnings: string[];
}
