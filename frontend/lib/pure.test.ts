import { describe, it, expect } from "vitest";
import {
  resolveImageUrl,
  formatSimilarityScore,
  filterSitesClientSide,
  moveStopIds,
} from "./api";
import type { SiteSummary } from "./types";

describe("resolveImageUrl pure function", () => {
  it("resolves relative backend file paths to full URLs", () => {
    const resolved = resolveImageUrl("/files/stepwell_1.jpg");
    expect(resolved).toContain("/files/stepwell_1.jpg");
    expect(resolved.startsWith("http")).toBe(true);
  });

  it("handles relative path without leading slash", () => {
    const resolved = resolveImageUrl("files/photo.jpg");
    expect(resolved).toContain("/files/photo.jpg");
    expect(resolved.startsWith("http")).toBe(true);
  });

  it("preserves external https URLs as-is", () => {
    const external = "https://example.org/heritage/rani.jpg";
    expect(resolveImageUrl(external)).toBe(external);
  });

  it("preserves local placeholder assets without prepending backend host", () => {
    const placeholder = "/placeholders/stepwell-rani.svg";
    expect(resolveImageUrl(placeholder)).toBe(placeholder);
  });

  it("handles null or undefined safely", () => {
    expect(resolveImageUrl(null)).toBe("");
    expect(resolveImageUrl(undefined)).toBe("");
    expect(resolveImageUrl("")).toBe("");
  });
});

describe("formatSimilarityScore pure function", () => {
  it("formats positive cosine similarity scores to 2 decimal places", () => {
    expect(formatSimilarityScore(0.826)).toBe("0.83");
    expect(formatSimilarityScore(0.5)).toBe("0.50");
    expect(formatSimilarityScore(1)).toBe("1.00");
  });

  it("formats negative cosine scores", () => {
    expect(formatSimilarityScore(-0.354)).toBe("-0.35");
  });

  it("safely handles NaN", () => {
    expect(formatSimilarityScore(NaN)).toBe("0.00");
  });
});

describe("filterSitesClientSide pure function", () => {
  const sampleSites: SiteSummary[] = [
    { id: 1, name: "Rani ki Vav", region: "Gujarat", category: "stepwell", lat: 23.85, lon: 72.1 },
    { id: 2, name: "Adalaj Stepwell", region: "Gujarat", category: "stepwell", lat: 23.16, lon: 72.58 },
    { id: 3, name: "Sun Temple, Modhera", region: "Gujarat", category: "temple", lat: 23.58, lon: 72.13 },
    { id: 4, name: "Kumbhalgarh Fort", region: "Rajasthan", category: "fort", lat: 25.14, lon: 73.58 },
  ];

  it("filters sites by category case-insensitively", () => {
    const forts = filterSitesClientSide(sampleSites, { category: "fort" });
    expect(forts).toHaveLength(1);
    expect(forts[0].name).toBe("Kumbhalgarh Fort");

    const stepwells = filterSitesClientSide(sampleSites, { category: "Stepwell" });
    expect(stepwells).toHaveLength(2);
  });

  it("filters sites by text query matching name or region", () => {
    const rajasthan = filterSitesClientSide(sampleSites, { query: "rajasthan" });
    expect(rajasthan).toHaveLength(1);
    expect(rajasthan[0].name).toBe("Kumbhalgarh Fort");

    const modhera = filterSitesClientSide(sampleSites, { query: "modhera" });
    expect(modhera).toHaveLength(1);
    expect(modhera[0].name).toBe("Sun Temple, Modhera");
  });

  it("returns all sites when query and category are empty", () => {
    const all = filterSitesClientSide(sampleSites, {});
    expect(all).toHaveLength(4);
  });
});

describe("moveStopIds pure function", () => {
  const ids = [10, 20, 30];

  it("moves a stop up one position", () => {
    expect(moveStopIds(ids, 20, -1)).toEqual([20, 10, 30]);
  });

  it("moves a stop down one position", () => {
    expect(moveStopIds(ids, 20, 1)).toEqual([10, 30, 20]);
  });

  it("keeps the order when a move would leave the list", () => {
    expect(moveStopIds(ids, 10, -1)).toEqual(ids);
    expect(moveStopIds(ids, 30, 1)).toEqual(ids);
  });

  it("keeps the order for an unknown stop id", () => {
    expect(moveStopIds(ids, 999, 1)).toEqual(ids);
  });

  it("does not mutate the input array", () => {
    const original = [10, 20, 30];
    moveStopIds(original, 10, 1);
    expect(original).toEqual([10, 20, 30]);
  });
});
