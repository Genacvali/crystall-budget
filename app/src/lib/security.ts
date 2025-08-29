import * as a2 from '@node-rs/argon2';

export async function hashPassword(password: string): Promise<string> {
  return a2.hash(password);
}

export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  try {
    return await a2.verify(hash, password);
  } catch (error) {
    return false;
  }
}

export function validateEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

export function validatePassword(password: string): { isValid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  if (password.length < 8) {
    errors.push('Пароль должен содержать минимум 8 символов');
  }
  
  if (!/[A-Z]/.test(password)) {
    errors.push('Пароль должен содержать заглавную букву');
  }
  
  if (!/[a-z]/.test(password)) {
    errors.push('Пароль должен содержать строчную букву');
  }
  
  if (!/[0-9]/.test(password)) {
    errors.push('Пароль должен содержать цифру');
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
}