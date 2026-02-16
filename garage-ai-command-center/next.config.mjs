/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "upload.wikimedia.org" },
      { protocol: "https", hostname: "commons.wikimedia.org" },
    ],
  },
  async rewrites() {
    const bridgeUrl = process.env.NEXT_PUBLIC_BRIDGE_URL || "http://localhost:8000"
    return [
      {
        source: "/api/:path*",
        destination: `${bridgeUrl}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
