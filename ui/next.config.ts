import type { NextConfig } from 'next'

// Static export: no Node process exists at runtime (REBUILD-UI D19). Every
// route becomes a folder with an index.html, so the engine's manifest maps a
// route to exactly one file with no path arithmetic.
const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  images: { unoptimized: true },
}

export default nextConfig
