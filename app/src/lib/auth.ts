import { NextAuthOptions } from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import { prisma } from './db';
import { verifyPassword } from './security';

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      id: 'credentials',
      name: 'Email & Password',
      credentials: {
        email: { 
          label: 'Email', 
          type: 'email',
          placeholder: 'your@email.com'
        },
        password: { 
          label: 'Password', 
          type: 'password' 
        },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null;
        }

        try {
          const user = await prisma.user.findUnique({
            where: { email: credentials.email.toLowerCase() },
            include: {
              households: {
                include: {
                  household: true
                }
              }
            }
          });

          if (!user) {
            return null;
          }

          const isValid = await verifyPassword(credentials.password, user.passwordHash);
          if (!isValid) {
            return null;
          }

          return {
            id: user.id,
            email: user.email,
            households: user.households.map(hm => ({
              id: hm.household.id,
              name: hm.household.name,
              role: hm.role
            }))
          };
        } catch (error) {
          console.error('Auth error:', error);
          return null;
        }
      },
    }),
  ],
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  jwt: {
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.households = user.households;
      }
      return token;
    },
    async session({ session, token }) {
      if (token) {
        session.user.id = token.sub!;
        session.user.households = token.households as any;
      }
      return session;
    },
  },
  pages: {
    signIn: '/auth/signin',
    signUp: '/auth/signup',
    error: '/auth/error',
  },
  secret: process.env.NEXTAUTH_SECRET,
};

declare module 'next-auth' {
  interface User {
    households: Array<{
      id: string;
      name: string;
      role: string;
    }>;
  }

  interface Session {
    user: {
      id: string;
      email: string;
      households: Array<{
        id: string;
        name: string;
        role: string;
      }>;
    };
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    households: Array<{
      id: string;
      name: string;
      role: string;
    }>;
  }
}