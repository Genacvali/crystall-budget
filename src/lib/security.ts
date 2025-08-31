import { hash, verify } from '@node-rs/argon2';

const HASH_OPTIONS = {
  memoryCost: 65536, // 64 MB
  timeCost: 3,       // 3 iterations  
  parallelism: 4,    // 4 threads
  outputLen: 32,     // 32 byte hash
};

export async function hashPassword(password: string): Promise<string> {
  try {
    return await hash(password, HASH_OPTIONS);
  } catch (error) {
    console.error('Password hashing error:', error);
    throw new Error('Failed to hash password');
  }
}

export async function verifyPassword(password: string, hashedPassword: string): Promise<boolean> {
  try {
    return await verify(hashedPassword, password);
  } catch (error) {
    console.error('Password verification error:', error);
    return false;
  }
}

export function generateSecureId(): string {
  return Math.random().toString(36).substring(2) + Date.now().toString(36);
}