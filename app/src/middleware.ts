import { withAuth } from 'next-auth/middleware';

export default withAuth(
  function middleware(req) {
    // Additional middleware logic can go here
  },
  {
    callbacks: {
      authorized: ({ token, req }) => {
        // Public routes that don't require authentication
        const publicRoutes = ['/auth/signin', '/auth/signup', '/auth/error'];
        const isPublicRoute = publicRoutes.some(route => req.nextUrl.pathname.startsWith(route));
        
        if (isPublicRoute) {
          return true;
        }
        
        // Protected routes require authentication
        return !!token;
      },
    },
  }
);

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api/auth (authentication endpoints)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files (icons, manifest, etc.)
     */
    '/((?!api/auth|_next/static|_next/image|favicon.ico|icons|manifest.json|sw.js|service-worker.js).*)',
  ],
};