import type {
  AddTagResponse,
  AIChatMessage,
  AIChatResponse,
  AddTrailStopInput,
  CreateTrailInput,
  GetSitesParams,
  ImageSearchResult,
  JobStatusResponse,
  RelatedSite,
  ReviewHistoryEntry,
  ReviewQueueItem,
  ReviewTagResponse,
  SiteDetail,
  SiteSummary,
  TagStatus,
  TextSearchResult,
  Trail,
  TrailFromImagesInput,
  TrailFromImagesResult,
  TrailJournal,
  TrailStop,
  TrailSummary,
  UpdateTrailInput,
  UploadResponse,
} from "./types";
import { MOCK_SITES } from "./mocks/sites";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

/**
 * Typed error class for API failures
 */
export class ApiError extends Error {
  readonly status: number;
  readonly detail?: string;

  constructor(message: string, status = 500, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Pure URL helper: turns relative paths like "/files/x.jpg" into full URLs using NEXT_PUBLIC_API_URL.
 * Preserves local static /placeholders/ assets and existing absolute URLs.
 */
export function resolveImageUrl(path: string | undefined | null): string {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("data:")) {
    return path;
  }
  if (path.startsWith("/placeholders/")) {
    return path;
  }
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${cleanPath}`;
}

/**
 * Pure formatting helper for cosine similarity scores [-1, 1]
 */
export function formatSimilarityScore(score: number): string {
  if (Number.isNaN(score)) return "0.00";
  return score.toFixed(2);
}

/**
 * Pure client-side filtering function
 */
export function filterSitesClientSide(
  sites: SiteSummary[],
  options: {
    category?: string;
    verifiedOnly?: boolean;
    query?: string;
    siteDetailsMap?: Record<number, SiteDetail>;
  }
): SiteSummary[] {
  let result = [...sites];

  if (options.query && options.query.trim()) {
    const q = options.query.toLowerCase().trim();
    result = result.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.region.toLowerCase().includes(q) ||
        s.category.toLowerCase().includes(q)
    );
  }

  if (options.category && options.category.trim()) {
    const cat = options.category.toLowerCase().trim();
    result = result.filter((s) => s.category.toLowerCase() === cat);
  }

  if (options.verifiedOnly && options.siteDetailsMap) {
    result = result.filter((s) => {
      const detail = options.siteDetailsMap?.[s.id];
      if (!detail) return true;
      return detail.images.some((img) => img.tags.some((t) => t.status === "verified"));
    });
  }

  return result;
}

/**
 * Pure helper: moves one stop id up or down. Returns the original order when the
 * move would fall outside the list.
 */
export function moveStopIds(
  stopIds: number[],
  stopId: number,
  direction: -1 | 1
): number[] {
  const from = stopIds.indexOf(stopId);
  const to = from + direction;
  if (from === -1 || to < 0 || to >= stopIds.length) return [...stopIds];
  const next = [...stopIds];
  [next[from], next[to]] = [next[to], next[from]];
  return next;
}

/**
 * Internal request helper
 */
async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
  let res: Response;
  try {
    res = await fetch(url, {
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...init?.headers,
      },
      ...init,
    });
  } catch (err: unknown) {
    throw new ApiError(
      "Couldn't reach server. Check your connection or verify the backend is running.",
      0,
      err instanceof Error ? err.message : String(err)
    );
  }

  if (!res.ok) {
    let errorDetail: string | undefined;
    try {
      const body = (await res.json()) as { detail?: string };
      errorDetail = body.detail;
    } catch {
      // Body not JSON
    }
    const message =
      errorDetail ||
      (res.status === 404
        ? "Requested resource was not found."
        : `Request failed with status ${res.status}.`);
    throw new ApiError(message, res.status, errorDetail);
  }

  return (await res.json()) as T;
}

// ----------------------------------------------------------------------
// API Call Implementations (Real + Typed Mocks)
// ----------------------------------------------------------------------

/**
 * GET /sites
 * Supports region filter on backend; type/verified filtered client-side per tasks.
 */
export async function getSites(params?: GetSitesParams): Promise<SiteSummary[]> {
  if (USE_MOCKS) {
    await new Promise((r) => setTimeout(r, 60));
    let filtered = MOCK_SITES;
    if (params?.region) {
      const reg = params.region.toLowerCase();
      filtered = filtered.filter((s) => s.region.toLowerCase() === reg);
    }

    if (params?.category) {
      const cat = params.category.toLowerCase();
      filtered = filtered.filter((s) => s.category.toLowerCase() === cat);
    }
    if (params?.verified_only) {
      filtered = filtered.filter((s) =>
        s.images.some((img) => img.tags.some((t) => t.status === "verified"))
      );
    }
    return filtered.map(({ id, name, region, category, lat, lon }) => ({
      id,
      name,
      region,
      category,
      lat,
      lon,
    }));
  }

  const query = new URLSearchParams();
  if (params?.region) query.set("region", params.region);
  const qs = query.toString();
  return fetchJson<SiteSummary[]>(`/sites${qs ? `?${qs}` : ""}`);
}

export async function askHeritage(
  question: string,
  history: AIChatMessage[] = [],
  siteId?: number,
  imageId?: number
): Promise<AIChatResponse> {
  return fetchJson<AIChatResponse>("/ai/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      history: history.slice(-10),
      site_id: siteId ?? null,
      image_id: imageId ?? null,
    }),
  });
}

/**
 * GET /sites/{id}
 */
export async function getSite(id: number): Promise<SiteDetail> {
  if (USE_MOCKS) {
    await new Promise((r) => setTimeout(r, 60));
    const site = MOCK_SITES.find((s) => s.id === id);
    if (!site) {
      throw new ApiError(`Site #${id} not found. Return to map or pick another site.`, 404);
    }
    return site;
  }

  return fetchJson<SiteDetail>(`/sites/${id}`);
}

export const getSiteById = getSite;

/**
 * GET /search/text?q=&k=10
 */
export async function searchText(q: string, k = 10): Promise<TextSearchResult[]> {
  if (USE_MOCKS) {
    await new Promise((r) => setTimeout(r, 80));
    const term = q.toLowerCase().trim();
    if (!term) return [];
    return MOCK_SITES.filter(
      (s) =>
        s.name.toLowerCase().includes(term) ||
        s.description.toLowerCase().includes(term) ||
        s.region.toLowerCase().includes(term)
    )
      .slice(0, k)
      .map((s, idx) => ({
        id: s.id,
        name: s.name,
        region: s.region,
        description: s.description,
        score: Math.max(0.4, Number((0.92 - idx * 0.08).toFixed(2))),
      }));
  }

  const query = new URLSearchParams({ q, k: String(k) });
  return fetchJson<TextSearchResult[]>(`/search/text?${query.toString()}`);
}

/**
 * GET /search/images?q=&k=10
 */
export async function searchImages(q: string, k = 10): Promise<ImageSearchResult[]> {
  if (USE_MOCKS) {
    await new Promise((r) => setTimeout(r, 80));
    const term = q.toLowerCase().trim();
    if (!term) return [];
    const results: ImageSearchResult[] = [];
    for (const site of MOCK_SITES) {
      for (const img of site.images) {
        const matchesTag = img.tags.some((t) => t.label.toLowerCase().includes(term));
        const matchesName = site.name.toLowerCase().includes(term);
        const matchesCategory = site.category.toLowerCase().includes(term);
        if (matchesTag || matchesName || matchesCategory) {
          results.push({
            image_id: img.id,
            site_id: site.id,
            name: site.name,
            region: site.region,
            url: img.url,
            score: 0.84,
          });
        }
      }
    }
    // Fallback if none matched
    if (results.length === 0) {
      return [
        {
          image_id: 101,
          site_id: 1,
          name: "Rani ki Vav",
          region: "Gujarat",
          url: "/placeholders/stepwell-rani.svg",
          score: 0.65,
        },
      ];
    }
    return results.slice(0, k);
  }

  const query = new URLSearchParams({ q, k: String(k) });
  return fetchJson<ImageSearchResult[]>(`/search/images?${query.toString()}`);
}

/**
 * POST /search/by-image
 */
export async function searchByImage(file: File, k = 10): Promise<ImageSearchResult[]> {
  if (USE_MOCKS) {
    await new Promise((r) => setTimeout(r, 120));
    return [
      {
        image_id: 101,
        site_id: 1,
        name: "Rani ki Vav",
        region: "Gujarat",
        url: "/placeholders/stepwell-rani.svg",
        score: 0.88,
      },
      {
        image_id: 104,
        site_id: 4,
        name: "Chand Baori",
        region: "Rajasthan",
        url: "/placeholders/stepwell-chandbaori.svg",
        score: 0.81,
      },
      {
        image_id: 102,
        site_id: 2,
        name: "Adalaj Stepwell",
        region: "Gujarat",
        url: "/placeholders/stepwell-adalaj.svg",
        score: 0.76,
      },
    ].slice(0, k);
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("k", String(k));

  const url = `${API_BASE}/search/by-image`;
  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { Accept: "application/json" },
      body: formData,
    });
  } catch (err: unknown) {
    throw new ApiError(
      "Couldn't connect to visual search service.",
      0,
      err instanceof Error ? err.message : String(err)
    );
  }

  if (!res.ok) {
    throw new ApiError(`Visual search failed with status ${res.status}.`, res.status);
  }

  return (await res.json()) as ImageSearchResult[];
}

/**
 * POST /images/upload
 */
export async function uploadImage(data: FormData): Promise<UploadResponse> {
  if (USE_MOCKS) {
    await new Promise((r) => setTimeout(r, 150));
    const randomJobId = Math.floor(Math.random() * 9000) + 1000;
    const randomImgId = Math.floor(Math.random() * 900) + 200;
    return {
      site_id: 1,
      image_id: randomImgId,
      job_id: randomJobId,
      status: "queued",
      duplicate: false,
      url: "/placeholders/stepwell-rani.svg",
    };
  }

  const url = `${API_BASE}/images/upload`;
  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { Accept: "application/json" },
      body: data,
    });
  } catch (err: unknown) {
    throw new ApiError(
      "Couldn't upload photo. Check your connection or try again.",
      0,
      err instanceof Error ? err.message : String(err)
    );
  }

  if (!res.ok) {
    throw new ApiError(`Upload failed with status ${res.status}.`, res.status);
  }

  return (await res.json()) as UploadResponse;
}

/**
 * GET /jobs/{id}
 */
export async function getJob(id: number): Promise<JobStatusResponse> {
  if (USE_MOCKS) {
    await new Promise((r) => setTimeout(r, 50));
    // In mock mode, mark job as completed after polling
    return {
      id,
      status: "done",
      error: null,
    };
  }

  return fetchJson<JobStatusResponse>(`/jobs/${id}`);
}

/**
 * GET /review/queue?limit=50&status=auto
 */
export async function getReviewQueue(
  limit = 50,
  status: TagStatus = "auto"
): Promise<ReviewQueueItem[]> {
  if (USE_MOCKS) {
    await new Promise((r) => setTimeout(r, 50));
    if (status !== "auto") return [];
    const mockQueue: ReviewQueueItem[] = [
      {
        id: 9,
        image_id: 101,
        site_id: 1,
        site_name: "Rani ki Vav",
        label: "jali work",
        tag_type: "feature",
        score: 0.23,
        status: "auto",
        created_at: "2026-11-01T10:00:00Z",
        url: "/placeholders/stepwell-rani.svg",
        author: "[Placeholder Contributor]",
        licence: "Placeholder (CC BY-SA 4.0)",
      },
      {
        id: 8,
        image_id: 102,
        site_id: 2,
        site_name: "Adalaj Stepwell",
        label: "stringcourse frieze",
        tag_type: "feature",
        score: 0.58,
        status: "auto",
        created_at: "2026-11-01T10:00:00Z",
        url: "/placeholders/stepwell-adalaj.svg",
        author: "[Placeholder Contributor]",
        licence: "Placeholder (CC BY-SA 4.0)",
      },
      {
        id: 12,
        image_id: 103,
        site_id: 3,
        site_name: "Sun Temple, Modhera",
        label: "sculptured plinth",
        tag_type: "feature",
        score: 0.64,
        status: "auto",
        created_at: "2026-11-01T10:00:00Z",
        url: "/placeholders/stepwell-rani.svg",
        author: "[Placeholder Contributor]",
        licence: "Placeholder (CC BY-SA 4.0)",
      },
    ];
    return mockQueue.slice(0, limit);
  }

  const query = new URLSearchParams({ limit: String(limit), status });
  return fetchJson<ReviewQueueItem[]>(`/review/queue?${query.toString()}`);
}

/**
 * GET /review/reviewers
 */
export async function getReviewers(): Promise<string[]> {
  if (USE_MOCKS) {
    await new Promise((r) => setTimeout(r, 30));
    return ["asha", "ravi", "guest"];
  }
  return fetchJson<string[]>("/review/reviewers");
}

/**
 * GET /review/history/{image_tag_id}
 */
export async function getReviewHistory(
  imageTagId: number
): Promise<ReviewHistoryEntry[]> {
  if (USE_MOCKS) {
    await new Promise((r) => setTimeout(r, 30));
    return [];
  }
  return fetchJson<ReviewHistoryEntry[]>(`/review/history/${imageTagId}`);
}

/**
 * POST /review/tags/{image_tag_id}
 */
export async function reviewTag(
  imageTagId: number,
  action: "confirm" | "reject",
  reviewer: string
): Promise<ReviewTagResponse> {
  if (USE_MOCKS) {
    await new Promise((r) => setTimeout(r, 60));
    const status = action === "confirm" ? "verified" : "rejected";
    return {
      id: imageTagId,
      status,
      previous_status: "auto",
      new_status: status,
    };
  }

  return fetchJson<ReviewTagResponse>(`/review/tags/${imageTagId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, reviewer }),
  });
}

/**
 * POST /review/tags/add
 */
export async function addTag(
  imageId: number,
  label: string,
  reviewer: string
): Promise<AddTagResponse> {
  if (USE_MOCKS) {
    await new Promise((r) => setTimeout(r, 60));
    return {
      id: Math.floor(Math.random() * 500) + 50,
      status: "added_by_human",
      previous_status: null,
      new_status: "added_by_human",
    };
  }

  return fetchJson<AddTagResponse>("/review/tags/add", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_id: imageId, label, reviewer }),
  });
}

/**
 * GET /sites/{id}/related
 */
export async function getRelatedSites(
  siteId: number,
  k = 5
): Promise<RelatedSite[]> {
  return fetchJson<RelatedSite[]>(`/sites/${siteId}/related?k=${k}`);
}

/**
 * GET /trails
 */
export async function getTrails(params?: {
  created_by?: string;
  is_public?: boolean;
  limit?: number;
  offset?: number;
}): Promise<Trail[]> {
  const query = new URLSearchParams();
  if (params?.created_by) query.set("created_by", params.created_by);
  if (typeof params?.is_public === "boolean") {
    query.set("is_public", String(params.is_public));
  }
  query.set("limit", String(params?.limit ?? 50));
  query.set("offset", String(params?.offset ?? 0));
  return fetchJson<Trail[]>(`/trails?${query.toString()}`);
}

/**
 * GET /trails/{id}
 */
export async function getTrail(trailId: number): Promise<Trail> {
  return fetchJson<Trail>(`/trails/${trailId}`);
}

/**
 * POST /trails
 */
export async function createTrail(input: CreateTrailInput): Promise<Trail> {
  return fetchJson<Trail>("/trails", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

/**
 * PATCH /trails/{id}
 */
export async function updateTrail(
  trailId: number,
  input: UpdateTrailInput
): Promise<Trail> {
  return fetchJson<Trail>(`/trails/${trailId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

/**
 * POST /trails/{id}/stops
 */
export async function addTrailStop(
  trailId: number,
  input: AddTrailStopInput
): Promise<TrailStop> {
  return fetchJson<TrailStop>(`/trails/${trailId}/stops`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

/**
 * DELETE /trails/{id}/stops/{stop_id}
 */
export async function removeTrailStop(
  trailId: number,
  stopId: number
): Promise<TrailStop[]> {
  return fetchJson<TrailStop[]>(`/trails/${trailId}/stops/${stopId}`, {
    method: "DELETE",
  });
}

/**
 * PATCH /trails/{id}/stops/reorder
 */
export async function reorderTrailStops(
  trailId: number,
  stopIds: number[]
): Promise<TrailStop[]> {
  return fetchJson<TrailStop[]>(`/trails/${trailId}/stops/reorder`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stop_ids: stopIds }),
  });
}

/**
 * POST /trails/from-images
 */
export async function createTrailFromImages(
  input: TrailFromImagesInput
): Promise<TrailFromImagesResult> {
  return fetchJson<TrailFromImagesResult>("/trails/from-images", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

/**
 * GET /trails/{id}/summary
 */
export async function getTrailSummary(trailId: number): Promise<TrailSummary> {
  return fetchJson<TrailSummary>(`/trails/${trailId}/summary`);
}

/**
 * GET /trails/{id}/journal
 */
export async function getTrailJournal(trailId: number): Promise<TrailJournal> {
  return fetchJson<TrailJournal>(`/trails/${trailId}/journal`);
}
