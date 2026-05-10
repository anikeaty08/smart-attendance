import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isPublicRoute = createRouteMatcher([
  "/",
  "/login(.*)",
]);

function claimRole(sessionClaims: Record<string, unknown> | null | undefined): string | null {
  if (!sessionClaims) return null;
  const metadata = sessionClaims.metadata as Record<string, unknown> | undefined;
  const publicMetadata = sessionClaims.public_metadata as Record<string, unknown> | undefined;
  const role = metadata?.role ?? publicMetadata?.role;
  return typeof role === "string" ? role : null;
}

export default clerkMiddleware(async (auth, request) => {
  const pathname = request.nextUrl.pathname;
  if (isPublicRoute(request)) return;

  const { userId, sessionClaims } = await auth();
  if (!userId) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (
    pathname.startsWith("/admin") ||
    pathname.startsWith("/hod") ||
    pathname.startsWith("/teacher")
  ) {
    const role = claimRole(sessionClaims as Record<string, unknown> | null | undefined);
    if (!role) {
      return NextResponse.redirect(new URL("/portal", request.url));
    }
    if (pathname.startsWith("/admin") && role !== "admin") {
      return NextResponse.redirect(new URL("/portal", request.url));
    }
    if (pathname.startsWith("/hod") && role !== "hod") {
      return NextResponse.redirect(new URL("/portal", request.url));
    }
    if (pathname.startsWith("/teacher") && role !== "faculty") {
      return NextResponse.redirect(new URL("/portal", request.url));
    }
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
