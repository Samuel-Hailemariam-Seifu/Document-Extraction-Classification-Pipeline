import type { NextConfig } from "next";

const backendUrl = (
  process.env.BACKEND_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000"
).replace(/\/$/, "");

const nextConfig: NextConfig = {
  // Allow HMR when opening the app via the LAN IP (e.g. phone/other machine)
  allowedDevOrigins: ["172.17.19.162"],
  // Proxy API + uploads through Next so browser URLs stay same-origin
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/uploads/:path*",
        destination: `${backendUrl}/uploads/:path*`,
      },
    ];
  },
};

export default nextConfig;
