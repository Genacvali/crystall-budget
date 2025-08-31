import { AuthService } from './auth';

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export class APIClient {
  private static async request<T>(
    path: string,
    init: RequestInit = {}
  ): Promise<T> {
    const token = AuthService.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((init.headers as Record<string, string>) || {})
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const res = await fetch(`/api${path}`, {
      ...init,
      headers
    });

    if (!res.ok) {
      let errorMessage = `HTTP ${res.status}`;
      let errorCode: string | undefined;

      try {
        const errorData = await res.json();
        errorMessage = errorData.error || errorMessage;
        errorCode = errorData.code;
      } catch {
        // If response is not JSON, use status text
        errorMessage = res.statusText || errorMessage;
      }

      throw new APIError(errorMessage, res.status, errorCode);
    }

    return res.json();
  }

  static async get<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: 'GET' });
  }

  static async post<T>(path: string, data?: any): Promise<T> {
    return this.request<T>(path, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined
    });
  }

  static async put<T>(path: string, data?: any): Promise<T> {
    return this.request<T>(path, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined
    });
  }

  static async delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: 'DELETE' });
  }

  // Health check
  static async health(): Promise<{ ok: boolean; ts: number }> {
    return this.get('/health');
  }
}