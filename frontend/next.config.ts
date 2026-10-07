import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Build plain static files into out/, so the Python backend can serve the screen itself.
  output: "export",
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
