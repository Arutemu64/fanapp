import createClient from "openapi-fetch";
import type { paths } from "$lib/api/v1";

type FetchImpl = typeof fetch;

interface RequestOptions extends RequestInit {
    params?: Record<string, string>;
    customFetch?: FetchImpl;
}

export class ApiError extends Error {
    constructor(public status: number, public message: string, public data?: any) {
        super(message);
        this.name = 'ApiError';
    }
}

class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
    }

    private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
        const { params, customFetch, ...init } = options;
        const fetchImpl = customFetch || fetch;
        
        const url = new URL(`${this.baseUrl}${endpoint}`);
        if (params) {
            Object.entries(params).forEach(([k, v]) => url.searchParams.append(k, v));
        }

        const response = await fetchImpl(url, {
            ...init,
            headers: { 'Content-Type': 'application/json', ...init.headers },
            credentials: 'include' 
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            throw new ApiError(response.status, errorData?.detail || response.statusText, errorData);
        }

        return response.status === 204 ? ({} as T) : await response.json();
    }

    get<T>(path: string, opts?: RequestOptions): Promise<T> {
        return this.request<T>(path, { ...opts, method: 'GET' });
    }
    
    post<T>(path: string, body: any, opts?: RequestOptions): Promise<T> {
        return this.request<T>(path, { 
            ...opts, 
            method: 'POST', 
            body: JSON.stringify(body) 
        });
    }

    put<T>(path: string, body: any, opts?: RequestOptions): Promise<T> {
        return this.request<T>(path, { 
            ...opts, 
            method: 'PUT', 
            body: JSON.stringify(body) 
        });
    }

    delete<T>(path: string, opts?: RequestOptions): Promise<T> {
        return this.request<T>(path, { ...opts, method: 'DELETE' });
    }
}

export const api = new ApiClient(import.meta.env.VITE_API_URL || 'http://127.0.0.1:8081');

export const client = createClient<paths>({ baseUrl: "http://127.0.0.1:8081" });