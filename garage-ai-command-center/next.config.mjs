/** @type {import('next').NextConfig} */
const isExport = process.env.NEXT_OUTPUT === 'export'

const nextConfig = {
  output: isExport ? 'export' : 'standalone',
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    ...(isExport ? { unoptimized: true } : {}),
    remotePatterns: [
      { protocol: "https", hostname: "upload.wikimedia.org" },
      { protocol: "https", hostname: "commons.wikimedia.org" },
    ],
  },
  // Rewrites only work in non-export mode (local dev)
  ...(isExport ? {} : {
    async rewrites() {
      const bridgeUrl = process.env.NEXT_PUBLIC_BRIDGE_URL || "http://localhost:8000"
      return [
        {
          source: "/api/:path*",
          destination: `${bridgeUrl}/api/:path*`,
        },
      ]
    },
  }),
}

export default nextConfig
