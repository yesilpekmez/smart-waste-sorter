import { CLASS_ORDER } from './constants';
import type { Detection, Operation, WasteClass } from './types';

// Backend bağlanana kadar kullanılan örnek veriler

export const initialFill: Record<WasteClass, number> = {
  plastic: 42,
  paper: 28,
  glass: 65,
  metal: 82,
};

export const initialDetection: Detection = {
  label: 'plastic',
  confidence: 0.94,
  box: { x: 39, y: 16, w: 22, h: 68 },
};

export const initialOperation: Operation = {
  id: 1,
  label: 'paper',
  confidence: 0.91,
  status: 'completed',
  time: new Date(),
};

export function randomDetection(): Detection {
  const label = CLASS_ORDER[Math.floor(Math.random() * CLASS_ORDER.length)];
  const w = 18 + Math.random() * 14;
  const h = 45 + Math.random() * 30;
  return {
    label,
    // Arada bir belirsiz tahmin üretir
    confidence: Math.random() < 0.15 ? 0.4 + Math.random() * 0.18 : 0.8 + Math.random() * 0.19,
    box: { x: 50 - w / 2, y: 50 - h / 2, w, h },
  };
}
