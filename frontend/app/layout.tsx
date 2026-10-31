import type { Metadata } from "next";
import { Spectral, Public_Sans, Noto_Sans_Gujarati, Noto_Sans_Devanagari } from "next/font/google";
import "./globals.css";

const spectral = Spectral({
  subsets: ["latin"],
  weight: ["400", "600"],
  variable: "--font-spectral",
  display: "swap",
});

const publicSans = Public_Sans({
  subsets: ["latin"],
  weight: ["400", "600"],
  variable: "--font-public-sans",
  display: "swap",
});

const notoGujarati = Noto_Sans_Gujarati({
  subsets: ["gujarati"],
  weight: ["400", "600"],
  variable: "--font-noto-gujarati",
  display: "swap",
});

const notoDevanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari"],
  weight: ["400", "600"],
  variable: "--font-noto-devanagari",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Heritage Atlas",
  description: "Explore and verify heritage architecture of stone stepwells, forts, and temples.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${spectral.variable} ${publicSans.variable} ${notoGujarati.variable} ${notoDevanagari.variable}`}
    >
      <body className="bg-stone text-ink font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
