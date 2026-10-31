import type { GetSitesParams, SiteDetail, SiteSummary } from "./types";
import { MOCK_SITES } from "./mocks/sites";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

/**
 * Filter mock sites according to GetSitesParams
 */
function filterMockSites(params?: GetSitesParams): SiteSummary[] {
  let filtered = MOCK_SITES;

  if (params?.region) {
    const regionLower = params.region.toLowerCase();
    filtered = filtered.filter((s) => s.region.toLowerCase() === regionLower);
  }

  if (params?.category) {
    const categoryLower = params.category.toLowerCase();
    filtered = filtered.filter((s) => s.category.toLowerCase() === categoryLower);
  }

  if (params?.tag) {
    const tagLower = params.tag.toLowerCase();
    filtered = filtered.filter((s) =>
      s.images.some((img) =>
        img.tags.some((t) => t.label.toLowerCase().includes(tagLower))
      )
    );
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

/**
 * GET /sites
 * Fetch list of sites matching optional filters
 */
export async function getSites(params?: GetSitesParams): Promise<SiteSummary[]> {
  if (USE_MOCKS) {
    // Simulate brief asynchronous tick
    await new Promise((resolve) => setTimeout(resolve, 80));
    return filterMockSites(params);
  }

  const query = new URLSearchParams();
  if (params?.region) query.set("region", params.region);
  if (params?.category) query.set("category", params.category);
  if (params?.tag) query.set("tag", params.tag);
  if (params?.verified_only !== undefined) {
    query.set("verified_only", String(params.verified_only));
  }

  const url = `${API_BASE}/sites${query.toString() ? `?${query.toString()}` : ""}`;

  try {
    const res = await fetch(url, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error("Couldn't load sites. Check your connection or try refreshing the page.");
    }

    const data = (await res.json()) as SiteSummary[];
    return data;
  } catch (err) {
    if (err instanceof Error) {
      throw err;
    }
    throw new Error("Couldn't load sites. Check your connection or try refreshing the page.");
  }
}

/**
 * GET /sites/{id}
 * Fetch full details for a single site
 */
export async function getSiteById(id: number): Promise<SiteDetail> {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, 60));
    const site = MOCK_SITES.find((s) => s.id === id);
    if (!site) {
      throw new Error(`Site #${id} not found. Select another site on the map.`);
    }
    return site;
  }

  const url = `${API_BASE}/sites/${id}`;

  try {
    const res = await fetch(url, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });

    if (!res.ok) {
      if (res.status === 404) {
        throw new Error(`Site #${id} not found. Select another site on the map.`);
      }
      throw new Error("Couldn't load site details. Check your connection or try refreshing the page.");
    }

    const data = (await res.json()) as SiteDetail;
    return data;
  } catch (err) {
    if (err instanceof Error) {
      throw err;
    }
    throw new Error("Couldn't load site details. Check your connection or try refreshing the page.");
  }
}
