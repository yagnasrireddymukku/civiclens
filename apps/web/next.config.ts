import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Workspace packages are consumed from source (no separate build step for
  // them at this phase) — see packages/types, packages/validation.
  transpilePackages: ["@civiclens/types", "@civiclens/validation"],
};

export default nextConfig;
