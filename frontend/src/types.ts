export type WasteClass = 'plastic' | 'paper' | 'glass' | 'metal';

export interface Detection {
  label: WasteClass;
  confidence: number; // 0–1
  // Kare içindeki konum, yüzde olarak
  box: { x: number; y: number; w: number; h: number };
}

export type SortStatus = 'ready' | 'sorting' | 'done' | 'bin_full' | 'uncertain';

export interface Operation {
  id: number;
  label: WasteClass;
  confidence: number;
  status: 'completed' | 'rejected';
  time: Date;
}
