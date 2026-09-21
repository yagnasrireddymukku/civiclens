import createMiddleware from "next-intl/middleware";
import { NextResponse, type NextRequest } from "next/server";
import { routing } from "./i18n/routing";

const intlMiddleware = createMiddleware(routing);

// Matches /en/dev/design-system, /te/dev/design-system, etc. — never a
// public CivicLens feature (this phase's §22). Blocked at the proxy
// layer, before any rendering happens, rather than relying solely on a
// notFound() call inside the page component — a stronger, simpler
// guarantee that doesn't depend on how a particular render path
// propagates a thrown not-found error.
const DEV_ONLY_PATH = /^\/[a-z]{2}\/dev(\/|$)/;

export default function proxy(request: NextRequest) {
  if (process.env.NODE_ENV === "production" && DEV_ONLY_PATH.test(request.nextUrl.pathname)) {
    return new NextResponse(null, { status: 404 });
  }

  return intlMiddleware(request);
}

export const config = {
  // Skip Next.js internals and static files; run on every real page route.
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
