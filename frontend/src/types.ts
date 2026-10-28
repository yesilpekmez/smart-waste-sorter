export type WasteClass = 'plastic' | 'paper' | 'glass' | 'metal';

export type BlockReason = 'uncertain' | 'bin_full';

export type OperationStatus = 'running' | 'completed' | 'rejected' | 'aborted' | 'failed';

export interface Operation {
  id: number;
  detectionId: number;
  label: WasteClass;
  confidence: number;
  modelVersion: string;
  targetBin: WasteClass;
  imageUrl: string | null;
  status: OperationStatus;
  // rejected: BlockReason — aborted: no_item — failed: kontrol servisinin hata kodu
  reason: string | null;
  message: string | null;
  minConfidence: number;
  fullThreshold: number;
  trace: [string, number][];
  durationMs: number | null;
  createdAt: string;
  finishedAt: string | null;
}

export interface Detection {
  id: number;
  label: WasteClass;
  confidence: number; // 0–1
  modelVersion: string;
  // Kare içindeki konum, yüzde olarak; sınıflandırma modelinde null
  box: { x: number; y: number; w: number; h: number } | null;
  imageUrl: string | null;
  createdAt: string;
  // Bu algılama işlendiyse sonucu
  operation: Operation | null;
  // Şu an ayırma başlatılabilir mi?
  sortable: boolean;
  refusal: { code: string; message: string } | null;
  // İşlenmemişse, ayırmayı engelleyecek yazılım kuralı
  blockedReason: BlockReason | null;
}

export interface Bin {
  type: WasteClass;
  fill: number;
  updatedAt: string;
}

export interface Health {
  status: string;
  classifier: string;
  modelVersion: string;
  hardware: string;
  minConfidence: number;
  fullThreshold: number;
}

export interface SystemStatus {
  state: 'idle' | 'routing' | 'dropping' | 'verifying' | 'returning' | 'fault';
  fault: { code: string; message: string } | null;
  itemPresent: boolean;
  runningOperationId: number | null;
}

export interface Stats {
  total: number;
  completed: number;
  rejected: number;
  aborted: number;
  failed: number;
  successRate: number | null;
  averageConfidence: number | null;
  averageDurationMs: number | null;
  byClass: Record<WasteClass, Record<Exclude<OperationStatus, 'running'>, number>>;
}
