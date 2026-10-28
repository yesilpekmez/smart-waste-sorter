import { Cylinder, Files, Milk, Wine, type LucideIcon } from 'lucide-react';
import type { Operation, WasteClass } from './types';

export const CLASSES: Record<WasteClass, { name: string; Icon: LucideIcon }> = {
  plastic: { name: 'Plastik', Icon: Milk },
  paper: { name: 'Kâğıt', Icon: Files },
  glass: { name: 'Cam', Icon: Wine },
  metal: { name: 'Metal', Icon: Cylinder },
};

export const CLASS_ORDER: WasteClass[] = ['plastic', 'paper', 'glass', 'metal'];

export const percent = (v: number) => `%${Math.round(v * 100)}`;

// Backend'deki işlem nedenleri ve hata kodları
export const REASON_TEXT: Record<string, string> = {
  uncertain: 'Belirsiz tahmin',
  bin_full: 'Bölme dolu',
  no_item: 'Platformda atık yok',
  jam: 'Sıkışma',
  position_error: 'Konum hatası',
  home_error: 'Referans hatası',
  timeout: 'Zaman aşımı',
  driver_error: 'Sürücü hatası',
  interrupted: 'Yarıda kaldı',
};

export const reasonText = (code: string | null) => (code ? (REASON_TEXT[code] ?? code) : '');

const STATUS_TEXT: Record<Operation['status'], string> = {
  running: 'Ayrılıyor',
  completed: 'Ayrıldı',
  rejected: 'Reddedildi',
  aborted: 'Başlatılamadı',
  failed: 'Arıza',
};

export function operationText(op: Operation): string {
  const reason = reasonText(op.reason);
  return reason && op.status !== 'completed' ? `${STATUS_TEXT[op.status]} · ${reason}` : STATUS_TEXT[op.status];
}

export const STATE_TEXT: Record<string, string> = {
  idle: 'Hazır',
  routing: 'Platform dönüyor',
  dropping: 'Atık bırakılıyor',
  verifying: 'Doğrulanıyor',
  returning: 'Referansa dönüyor',
  fault: 'Arıza',
};

export const formatTime = (iso: string) =>
  new Date(iso).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
