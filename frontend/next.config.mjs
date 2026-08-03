/** @type {import('next').NextConfig} */
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  // Proxy the API through Next in development so the browser makes
  // same-origin requests and CORS never becomes a setup step.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default nextConfig;
