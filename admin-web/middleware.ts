import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const isPublicRoute = createRouteMatcher([
  "/",
  "/login(.*)",
]);

export default clerkMiddleware(async (auth, request) => {
  const pathname = request.nextUrl.pathname;
  if (!isPublicRoute(request)) {
    const { userId, getToken } = await auth();
    if (!userId) {
      const loginUrl = new URL("/login", request.url);
      return NextResponse.redirect(loginUrl);
    }

    if (
      pathname.startsWith("/admin") ||
      pathname.startsWith("/hod") ||
      pathname.startsWith("/teacher")
    ) {
      try {
        const token = await getToken();
        const meRes = await fetch(`${API_BASE}/me`, {
          headers: { Authorization: `Bearer ${token}` },
          cache: "no-store",
        });
        if (!meRes.ok) {
          return NextResponse.redirect(new URL("/portal", request.url));
        }
        const me = await meRes.json();
        const role = me?.role as string;

        if (pathname.startsWith("/admin") && role !== "admin") {
          return NextResponse.redirect(new URL("/portal", request.url));
        }
        if (pathname.startsWith("/hod") && role !== "hod") {
          return NextResponse.redirect(new URL("/portal", request.url));
        }
        if (pathname.startsWith("/teacher") && role !== "faculty") {
          return NextResponse.redirect(new URL("/portal", request.url));
        }
      } catch {
        return NextResponse.redirect(new URL("/portal", request.url));
      }
    }
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
