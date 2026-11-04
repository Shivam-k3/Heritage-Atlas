import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  images: {
    // Next.js 16 blocks image optimization from private IPs. Allow the
    // localhost:8000 dev backend in development only, never in production;
    // remotePatterns below still limits fetches to localhost:8000.
    dangerouslyAllowLocalIP: process.env.NODE_ENV !== "production",
    qualities: [75, 90],
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
      },
    ],
  },
};

export default nextConfig;
