import Link from "next/link";

/**
 * Root-level fallback for a path that doesn't even match the locale
 * segment (docs/FRONTEND.md §7) — middleware normally redirects "/" to
 * a locale-prefixed path before this is ever reached; this only
 * matters for the rare request that bypasses that. The locale-aware
 * not-found experience lives at app/[locale]/not-found.tsx.
 */
export default function RootNotFound() {
  return (
    <html lang="en">
      <body>
        <main style={{ padding: "2rem" }}>
          <h1>Page not found</h1>
          <p>
            <Link href="/">Return home</Link>
          </p>
        </main>
      </body>
    </html>
  );
}
