import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output copies only the files the runtime actually
  // needs (plus a minimal Node server) into `.next/standalone`.
  // The Docker runtime stage then ships ~150 MB instead of the full
  // `node_modules`. See the official Next 16 Docker guide + fly.toml.
  output: "standalone",
};

export default nextConfig;
