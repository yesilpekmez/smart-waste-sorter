export type WasteClass = 'plastic' | 'paper' | 'glass' | 'metal';

export type BlockReason = 'uncertain' | 'bin_full';

export interface Detection {
  id: number;
  label: WasteClass;
  confidence: number; // 0–1
  // Kare içindeki konum, yüzde olarak
  box: { x: number; y: number; w: number; h: number };
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
  status: 'completed' | 'rejected';
  reason: BlockReason | null;
  createdAt: string;
}

export type SortStatus = 'idle' | 'ready' | 'sorting' | 'done' | BlockReason;
