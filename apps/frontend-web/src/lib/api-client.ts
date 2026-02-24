/**
 * HTTP API client for backend communication
 */

import { getAuthHeaders } from './auth';
import { createLogger } from './logger';
import type { IPCResult } from '../shared/types';

const log = createLogger('api-client');

// API base URL - defaults to /api (proxied in dev), can be set via env for remote deployments
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  body?: unknown;
  signal?: AbortSignal;
}

/**
 * Make an authenticated API request
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<IPCResult<T>> {
  const { method = 'GET', body, signal } = options;

  try {
    const headers: Record<string, string> = {
      ...getAuthHeaders(),
    };

    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMsg = errorData.detail || errorData.error || `HTTP ${response.status}: ${response.statusText}`;
      log.error(`API error: ${method} ${endpoint}`, { status: response.status, error: errorMsg });
      return {
        success: false,
        error: errorMsg,
      };
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return { success: true };
    }

    const data = await response.json();

    // Check if backend already wrapped the response in { success, data } format
    // to avoid double-wrapping
    if (
      data &&
      typeof data === 'object' &&
      'success' in data &&
      typeof data.success === 'boolean'
    ) {
      // Backend already wrapped - return as-is
      return data as IPCResult<T>;
    }

    // Raw data from backend - wrap it
    return { success: true, data };
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      log.debug(`Request aborted: ${method} ${endpoint}`);
      return { success: false, error: 'Request aborted' };
    }
    const errorMsg = error instanceof Error ? error.message : 'Unknown error';
    log.error(`Network error: ${method} ${endpoint}`, error);
    return {
      success: false,
      error: errorMsg,
    };
  }
}

/**
 * GET request helper
 */
export function get<T>(endpoint: string, signal?: AbortSignal): Promise<IPCResult<T>> {
  return apiRequest<T>(endpoint, { signal });
}

/**
 * POST request helper
 */
export function post<T>(endpoint: string, body?: unknown, signal?: AbortSignal): Promise<IPCResult<T>> {
  return apiRequest<T>(endpoint, { method: 'POST', body, signal });
}

/**
 * PUT request helper
 */
export function put<T>(endpoint: string, body?: unknown, signal?: AbortSignal): Promise<IPCResult<T>> {
  return apiRequest<T>(endpoint, { method: 'PUT', body, signal });
}

/**
 * DELETE request helper
 */
export function del<T>(endpoint: string, signal?: AbortSignal): Promise<IPCResult<T>> {
  return apiRequest<T>(endpoint, { method: 'DELETE', signal });
}

/**
 * PATCH request helper
 */
export function patch<T>(endpoint: string, body?: unknown, signal?: AbortSignal): Promise<IPCResult<T>> {
  return apiRequest<T>(endpoint, { method: 'PATCH', body, signal });
}
