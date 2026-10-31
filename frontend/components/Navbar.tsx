"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { label: "Explore", href: "/" },
  { label: "Search", href: "/search" },
  { label: "Upload", href: "/upload" },
  { label: "Trails", href: "/trails" },
  { label: "Review", href: "/review" },
];

export const Navbar: React.FC = () => {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full h-14 bg-paper border-b border-sandstone flex items-center justify-between px-4 sm:px-6">
      {/* Brand logo / mark */}
      <div className="flex items-center gap-3">
        <Link
          href="/"
          className="flex items-center gap-2 text-indigo focus-ring rounded-[6px] py-1 px-1.5"
        >
          {/* Stepped icon representation */}
          <svg
            className="w-5 h-5 text-indigo shrink-0"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M2 4h4v4h4v4h4v4h4" />
          </svg>
          <span className="font-serif font-semibold text-lg tracking-normal">
            Heritage Atlas
          </span>
        </Link>
      </div>

      {/* Desktop Navigation */}
      <nav aria-label="Main" className="hidden md:flex items-center gap-1">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`px-3 py-1.5 rounded-[6px] type-small transition-colors focus-ring ${
                isActive
                  ? "font-semibold text-indigo bg-stone border-b-2 border-indigo"
                  : "text-ink hover:text-indigo hover:bg-stone/50"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
        <Link
          href="/dev/components"
          className="ml-3 px-2.5 py-1 text-[13px] text-mute hover:text-indigo rounded-[6px] border border-sandstone/60 focus-ring"
        >
          Dev tokens
        </Link>
      </nav>

      {/* Mobile hamburger button */}
      <div className="md:hidden flex items-center">
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-expanded={mobileMenuOpen}
          aria-label="Toggle navigation menu"
          className="p-2 rounded-[6px] text-ink hover:bg-stone focus-ring"
        >
          <svg
            className="w-5 h-5"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            aria-hidden="true"
          >
            {mobileMenuOpen ? (
              <path d="M4 4L16 16M4 16L16 4" />
            ) : (
              <path d="M3 5h14M3 10h14M3 15h14" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile dropdown */}
      {mobileMenuOpen && (
        <nav
          aria-label="Mobile Navigation"
          className="absolute top-14 left-0 w-full bg-paper border-b border-sandstone shadow-[0_4px_12px_rgba(26,29,38,0.08)] flex flex-col p-4 space-y-2 md:hidden"
        >
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`px-3 py-2 rounded-[6px] type-small ${
                  isActive
                    ? "font-semibold text-indigo bg-stone border-l-2 border-indigo"
                    : "text-ink hover:bg-stone/50"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
          <div className="pt-2 border-t border-sandstone">
            <Link
              href="/dev/components"
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-1.5 text-[13px] text-mute hover:text-indigo"
            >
              Dev tokens &amp; components
            </Link>
          </div>
        </nav>
      )}
    </header>
  );
};
