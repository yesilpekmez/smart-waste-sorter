export type WasteClass = 'plastic' | 'paper' | 'glass' | 'metal';

export type BlockReason = 'uncertain' | 'bin_full';

export interface Detection {
  id: number;
  label: WasteClass;
  confidence: number; // 0–1
  // Kare içindeki konum, yüzde olarak; sınıflandırma modelinde null
  box: { x: number; y: number; w: number; h: number } | null;
  imageUrl: string | null;
  blockedReason: BlockReason | null;
  createdAt: string;
}

export interface Bin {
  type: WasteClass;
  fill: number;
  updatedAt: string;
}

export interface Operation {
  id: number;
  detectionId: number;
  label: WasteClass;
  confidence: number;
  targetBin: WasteClass;
  imageUrl: string | null;
  status: 'completed' | 'rejected' | 'failed';
  // rejected: BlockReason — failed: kontrol servisinin hata kodu
  reason: string | null;
  createdAt: string;
}

export type SortStatus = 'idle' | 'ready' | 'sorting' | 'done' | 'fault' | BlockReason;

export interface SystemStatus {
  state: 'idle' | 'routing' | 'dropping' | 'verifying' | 'returning' | 'fault';
  fault: { code: string; message: string } | null;
  itemPresent: boolean;
}

export interface Stats {
  total: number;
  completed: number;
  rejected: number;
  failed: number;
  successRate: number | null;
  averageConfidence: number | null;
  byClass: Record<WasteClass, { completed: number; rejected: number; failed: number }>;
}
