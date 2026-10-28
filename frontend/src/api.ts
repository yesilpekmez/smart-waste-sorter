import type { Bin, Detection, Health, Operation, Stats, SystemStatus } from './types';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
  }
}

// Sunucuya ulaşılamıyor (ağ hatası ya da geliştirme sunucusunun vekil hatası)
export class NetworkError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, init);
  } catch {
    throw new NetworkError('Sunucuya bağlanılamadı');
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    // Backend kapalıyken Vite gövdesiz 500 döndürür; bu bir API yanıtı değildir
    if (res.status >= 500 && !body?.error) throw new NetworkError('Sunucuya bağlanılamadı');
    throw new ApiError(body?.error ?? 'Beklenmeyen bir hata oluştu', res.status, body?.code);
  }
  return body as T;
}

const post = <T>(path: string, json?: unknown) =>
  request<T>(path, {
    method: 'POST',
    headers: json ? { 'Content-Type': 'application/json' } : undefined,
    body: json ? JSON.stringify(json) : undefined,
  });

export const api = {
  health: () => request<Health>('/health'),
  system: () => request<SystemStatus>('/system'),
  resetSystem: () => post<SystemStatus>('/system/reset'),
  bins: () => request<Bin[]>('/bins'),
  emptyBin: (type: string) => post<Bin>(`/bins/${type}/empty`),
  // Henüz algılama yoksa null
  latestDetection: () =>
    request<Detection>('/detections/latest').catch((e) => {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }),
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

  // Görüntü verilmezse yalnızca örnek sınıflandırıcı sonuç üretir
  detect: (image?: File) => {
    if (!image) return post<Detection>('/detect');
    const form = new FormData();
    form.append('image', image);
    return request<Detection>('/detect', { method: 'POST', body: form });
  },
};
