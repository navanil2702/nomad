/** @type {import('next').NextConfig} */

// Where FastAPI actually lives. `API_URL` is server-only, which is the point:
// the browser keeps calling its own origin and this rewrite forwards to the
// API, so there is no cross-origin request and no CORS configuration to get
// wrong — in development or in production.
const API_URL =
  process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default nextConfig;
