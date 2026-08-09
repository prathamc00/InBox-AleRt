import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const backendOrigin = process.env.BACKEND_ORIGIN ?? process.env.NEXT_PUBLIC_API_URL ?? "http://52.207.228.73:8000";
    return [
      {
        source: "/backend/:path*",
        destination: `${backendOrigin}/:path*`,
      },
    ];
  },

};

export default nextConfig;
