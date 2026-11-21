import { NextRequest, NextResponse } from "next/server";

// Cheap cookie-presence check for fast redirects — NOT the real auth
// boundary (System Architecture §5). The actual verification (does this
// token resolve to a live, unexpired Session row) happens in Java, on
// every request the frontend forwards it to.
const SESSION_COOKIE = "session";
const PUBLIC_PATHS = ["/login", "/register"];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  const isPublic =
    PUBLIC_PATHS.includes(pathname) ||
    pathname.startsWith("/_next") ||
    // Proxied to the backend (next.config.ts rewrites), which does its own
    // auth — redirecting here would break login/register themselves.
    pathname.startsWith("/api/") ||
    pathname.includes(".");

  if (isPublic) return NextResponse.next();

  const hasSessionCookie = Boolean(req.cookies.get(SESSION_COOKIE)?.value);

  if (!hasSessionCookie) {
    return NextResponse.redirect(new URL("/login", req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|.*\\..*).*)"],
};
