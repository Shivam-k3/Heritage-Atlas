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
  score: number;
  status: TagStatus;
}

export interface SiteImage {
  id: number;
  url: string;
  author: string;
  licence: string;
  source_url?: string;
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
