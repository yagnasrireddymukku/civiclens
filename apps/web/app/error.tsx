"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Phase 1 has no centralized error tracking yet (see
    // docs/OBSERVABILITY.md); console is the interim foundation.
    console.error(error);
  }, [error]);

  return (
    <main>
      <h1>Something went wrong</h1>
      <p>An unexpected error occurred while rendering this page.</p>
      <button type="button" onClick={() => reset()}>
        Try again
      </button>
    </main>
  );
}
