import type { NextConfig } from "next";

// Where /api/* is forwarded. In production (Vercel) JAVA_API_URL is the Cloud
// Run backend URL and NEXT_PUBLIC_JAVA_API_URL is the frontend's OWN origin:
// the browser calls /api same-origin and Vercel proxies it, so the backend's
// SameSite=Lax session cookie stays first-party (a direct *.vercel.app ->
// *.run.app call would be cross-site and never carry it). A proxy rule, not a
// local API route — the frontend still has no /api handlers of its own.
const backendUrl = process.env.JAVA_API_URL ?? "http://localhost:8080";

const nextConfig: NextConfig = {
  // Hide the Next.js dev-mode logo/indicator button in the bottom corner
  devIndicators: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};

export default nextConfig;
