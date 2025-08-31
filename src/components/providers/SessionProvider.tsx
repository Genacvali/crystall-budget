'use client';
import { SessionProvider as NextAuthProvider } from 'next-auth/react';
import * as React from 'react';

export function SessionProvider({ children, session }: { children: React.ReactNode; session: any }) {
  return <NextAuthProvider session={session}>{children}</NextAuthProvider>;
}