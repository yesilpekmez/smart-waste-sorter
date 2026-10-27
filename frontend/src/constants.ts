import { Cylinder, Files, Milk, Wine, type LucideIcon } from 'lucide-react';
import type { WasteClass } from './types';

export const CLASSES: Record<WasteClass, { name: string; Icon: LucideIcon }> = {
  plastic: { name: 'Plastik', Icon: Milk },
  paper: { name: 'Kâğıt', Icon: Files },
  glass: { name: 'Cam', Icon: Wine },
  metal: { name: 'Metal', Icon: Cylinder },
};

export const CLASS_ORDER: WasteClass[] = ['plastic', 'paper', 'glass', 'metal'];

// Bu oranın üzerindeki bölmelere atık gönderilmez
export const FULL_THRESHOLD = 90;

// Bu güvenin altındaki tahminlerde ayırma durdurulur
export const MIN_CONFIDENCE = 0.6;

export const percent = (v: number) => `%${Math.round(v * 100)}`;

// Kontrol servisinin hata kodları
export const FAULT_TEXT: Record<string, string> = {
  jam: 'Sıkışma',
  position_error: 'Konum hatası',
  home_error: 'Referans hatası',
  no_item: 'Platformda atık yok',
};
