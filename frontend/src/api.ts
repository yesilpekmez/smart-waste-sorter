import type { Bin, Detection, Operation } from './types';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(body.error ?? 'Beklenmeyen bir hata oluştu', res.status);
  return body as T;
}

const post = <T>(path: string, json?: unknown) =>
  request<T>(path, {
    method: 'POST',
    headers: json ? { 'Content-Type': 'application/json' } : undefined,
    body: json ? JSON.stringify(json) : undefined,
  });

export const api = {
  health: () => request<{ status: string; classifier: string }>('/health'),
  bins: () => request<Bin[]>('/bins'),
  emptyBin: (type: string) => post<Bin>(`/bins/${type}/empty`),
  latestDetection: () => request<Detection>('/detections/latest'),
  operations: (limit = 1) => request<Operation[]>(`/operations?limit=${limit}`),
  sort: (detectionId: number) => post<{ operation: Operation; bin: Bin }>('/sort', { detectionId }),

  // Görüntü verilmezse sunucu kameradan kare alınmış gibi davranır
  detect: (image?: File) => {
    if (!image) return post<Detection>('/detect');
    const form = new FormData();
    form.append('image', image);
    return request<Detection>('/detect', { method: 'POST', body: form });
  },
};
