import type { Bin, Detection, Operation, Stats, SystemStatus } from './types';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(body.error ?? 'Beklenmeyen bir hata oluştu', res.status, body.code);
  return body as T;
}

const post = <T>(path: string, json?: unknown) =>
  request<T>(path, {
    method: 'POST',
    headers: json ? { 'Content-Type': 'application/json' } : undefined,
    body: json ? JSON.stringify(json) : undefined,
  });

export const api = {
  health: () => request<{ status: string; classifier: string; hardware: string }>('/health'),
  system: () => request<SystemStatus>('/system'),
  resetSystem: () => post<SystemStatus>('/system/reset'),
  bins: () => request<Bin[]>('/bins'),
  emptyBin: (type: string) => post<Bin>(`/bins/${type}/empty`),
  latestDetection: () => request<Detection>('/detections/latest'),
  operations: (params: { limit?: number; offset?: number; label?: string; status?: string } = {}) => {
    const query = new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== '')
        .map(([k, v]) => [k, String(v)]),
    );
    return request<{ total: number; items: Operation[] }>(`/operations?${query}`);
  },
  stats: () => request<Stats>('/stats'),
  sort: (detectionId: number) => post<{ operation: Operation; bin: Bin }>('/sort', { detectionId }),

  // Görüntü verilmezse sunucu kameradan kare alınmış gibi davranır
  detect: (image?: File) => {
    if (!image) return post<Detection>('/detect');
    const form = new FormData();
    form.append('image', image);
    return request<Detection>('/detect', { method: 'POST', body: form });
  },
};
