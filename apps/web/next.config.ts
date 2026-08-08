import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server.js + only the traced node_modules, so deploy/web.Dockerfile
  // can ship a runtime layer without the dev dependency tree. No effect on `next dev`.
  output: "standalone",
  // Pin the workspace root to this app so Next doesn't infer a parent dir.
  turbopack: {
    root: import.meta.dirname,
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          // Mic is used by pronunciation/conversation; everything else is off.
          {
            key: "Permissions-Policy",
            value: "microphone=(self), camera=(), geolocation=(), payment=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
