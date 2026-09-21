import { getApiHealth } from "@/lib/api";

export default async function Home() {
  const health = await getApiHealth();

  return (
    <main>
      <h1>CivicLens</h1>
      <p>
        India&rsquo;s Personal Public-Information Intelligence Platform — this is the Phase 1
        monorepo foundation, not the product homepage. See <code>docs/ROADMAP.md</code> for what
        comes next.
      </p>

      <section aria-label="Backend API status">
        <h2>API status</h2>
        {health.reachable ? (
          <p>
            Reachable — <strong>{health.data.status}</strong> ({health.data.service} v
            {health.data.version})
          </p>
        ) : (
          <p>
            Not reachable from this page ({health.error}). Start <code>apps/api</code> and reload to
            see a live status.
          </p>
        )}
      </section>
    </main>
  );
}
