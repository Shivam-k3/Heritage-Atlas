"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { askHeritage, getSite, getSites, resolveImageUrl } from "@/lib/api";
import type { AIChatMessage, AIChatResponse, SiteDetail, SiteSummary } from "@/lib/types";

const FEATURED_IDS = [1, 2, 11, 18, 24, 30];
const QUESTIONS = [
  "Which sites have stepwell architecture?",
  "Find heritage sites with carved stone details.",
  "Explain the architecture of Rani ki Vav.",
];

function PhotoCredit({ site }: { site: SiteDetail }) {
  const image = site.images[0];
  if (!image) return null;
  return (
    <span className="cinema-credit">
      Photo by {image.author} · {image.licence}
    </span>
  );
}

export function CinematicHome() {
  const [sites, setSites] = useState<SiteSummary[]>([]);
  const [featured, setFeatured] = useState<SiteDetail[]>([]);
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<AIChatMessage[]>([]);
  const [answer, setAnswer] = useState<AIChatResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void getSites()
      .then((data) => {
        if (!active) return;
        setSites(data);
        const ids = FEATURED_IDS.filter((id) => data.some((site) => site.id === id)).slice(0, 6);
        return Promise.all(ids.map((id) => getSite(id)));
      })
      .then((data) => {
        if (active && data) setFeatured(data.filter((site) => site.images.length > 0));
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  const hero = featured[0];
  const gallery = useMemo(() => featured.slice(1, 5), [featured]);

  async function submitQuestion(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || isLoading) return;
    const nextHistory = [...history, { role: "user" as const, content: trimmed }];
    setIsLoading(true);
    setError(null);
    try {
      const result = await askHeritage(trimmed, history);
      setAnswer(result);
      setHistory([...nextHistory, { role: "assistant", content: result.response }]);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ask Heritage Atlas is unavailable.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="cinema-shell">
      <section className="cinema-hero">
        <div className="cinema-hero-image">
          {hero?.images[0] && (
            <Image
              fill
              priority
              sizes="100vw"
              quality={90}
              src={resolveImageUrl(hero.images[0].url)}
              alt={hero.name}
            />
          )}
        </div>
        <div className="cinema-hero-scrim" />
        <div className="cinema-hero-content">
          <p className="cinema-kicker">A living archive of Indian architecture</p>
          <h1>Stone, light,<br /><em>memory.</em></h1>
          <p className="cinema-lede">
            Explore 30 documented heritage sites through field photographs, original notes and
            verified provenance.
          </p>
          <div className="flex flex-wrap gap-3">
            <a href="#explore-map" className="cinema-button cinema-button-light">Explore heritage</a>
            <a href="#ask-heritage" className="cinema-button cinema-button-ghost">Ask Heritage Atlas <span>↗</span></a>
          </div>
          {hero && <PhotoCredit site={hero} />}
        </div>
        <div className="cinema-hero-index">01 <span>/</span> 30 sites</div>
      </section>

      <section className="cinema-section cinema-intro">
        <div>
          <p className="cinema-kicker cinema-dark-kicker">Discover India&apos;s heritage</p>
          <h2>Every stone<br /><em>keeps a story.</em></h2>
        </div>
        <p className="cinema-copy">
          A curated visual atlas of stepwells, forts, temples and palaces across Gujarat and
          Rajasthan. Search by architectural detail, follow a trail, or simply wander.
        </p>
      </section>

      <section className="cinema-gallery cinema-section" aria-label="Featured heritage photographs">
        {gallery.map((site, index) => {
          const image = site.images[0];
          return (
            <Link key={site.id} href={`/sites/${site.id}`} className={`cinema-gallery-card cinema-gallery-${index + 1}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={resolveImageUrl(image.url)} alt={`${site.name} in ${site.region}`} loading="lazy" />
              <div className="cinema-gallery-overlay">
                <span>{site.category}</span>
                <strong>{site.name}</strong>
                <PhotoCredit site={site} />
              </div>
            </Link>
          );
        })}
      </section>

      <section id="ask-heritage" className="cinema-ai cinema-section">
        <div className="cinema-ai-heading">
          <p className="cinema-kicker">Ask Heritage Atlas</p>
          <h2>A thoughtful guide<br /><em>to what you see.</em></h2>
          <p className="cinema-copy">Ask about real records in the archive. Every answer is labelled and sourced.</p>
        </div>
        <div className="cinema-ai-panel">
          <form onSubmit={submitQuestion} className="cinema-ai-form">
            <label htmlFor="heritage-question">What would you like to discover?</label>
            <div className="cinema-ai-input">
              <input id="heritage-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Try “Find Jain temples with carved stone details”" />
              <button type="submit" disabled={!question.trim() || isLoading} aria-label="Ask Heritage Atlas">
                {isLoading ? "…" : "↗"}
              </button>
            </div>
          </form>
          <div className="cinema-suggestions">
            {QUESTIONS.map((item) => <button key={item} type="button" onClick={() => setQuestion(item)}>{item}</button>)}
          </div>
          {error && <p className="cinema-ai-error">{error}</p>}
          {answer && (
            <div className="cinema-answer" aria-live="polite">
              <div className="cinema-answer-label">{answer.ai_generated ? "AI-generated interpretation" : "Archive results"} · {answer.intent.replaceAll("_", " ")}</div>
              <p>{answer.response}</p>
              {answer.sites.length > 0 && <div className="cinema-answer-sites">{answer.sites.map((site) => <Link key={site.id} href={`/sites/${site.id}`}>{site.name} ↗</Link>)}</div>}
              {answer.warnings.map((warning) => <small key={warning}>{warning}</small>)}
            </div>
          )}
        </div>
      </section>

      <section className="cinema-location cinema-section">
        <div>
          <p className="cinema-kicker cinema-dark-kicker">Architecture &amp; culture</p>
          <h2>Look closer.<br /><em>Stay longer.</em></h2>
        </div>
        <div className="cinema-location-stat"><strong>{sites.length || 30}</strong><span>documented sites<br />to wander through</span></div>
      </section>
    </div>
  );
}
