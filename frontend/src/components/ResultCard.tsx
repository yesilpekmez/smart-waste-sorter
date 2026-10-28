import { ArrowRight } from 'lucide-react';
import { CLASSES, STATE_TEXT, percent, reasonText } from '../constants';
import type { Detection, SystemStatus } from '../types';

export type PanelStatus =
  | 'idle'
  | 'ready'
  | 'uncertain'
  | 'bin_full'
  | 'stale'
  | 'sorting'
  | 'done'
  | 'rejected'
  | 'aborted'
  | 'recovered'
  | 'fault';

const STATUS: Record<PanelStatus, { text: string; hint?: string; warn?: boolean }> = {
  idle: { text: 'Atık bekleniyor', hint: 'Kameradan kare al ya da fotoğraf yükle.' },
  ready: { text: 'Ayırmaya hazır' },
  uncertain: {
    text: 'Tahmin belirsiz',
    hint: 'Güven eşiğin altında; atık ayrılmaz. Reddedip atığı elle al ya da yeniden analiz et.',
    warn: true,
  },
  bin_full: { text: 'Bölme dolu', hint: 'Bölmeyi boşaltınca atık ayrılabilir.', warn: true },
  stale: { text: 'Tahmin geçersiz', hint: 'Bu karar daha yeni bir algılamayla geçersiz kaldı.', warn: true },
  sorting: { text: 'Ayrılıyor…' },
  done: { text: 'Ayrıldı', hint: 'Sıradaki atığı platforma koyup analiz et.' },
  rejected: { text: 'Reddedildi', hint: 'Atığı platformdan elle al; sonra sıradakini analiz et.', warn: true },
  aborted: { text: 'Platformda atık yok', hint: 'Atık analizden sonra alınmış. Yeni atığı analiz et.', warn: true },
  recovered: {
    text: 'Arıza giderildi',
    hint: 'Atık hâlâ platformda olabilir; yeniden analiz et.',
    warn: true,
  },
  fault: { text: 'Arıza · Sistem durdu', hint: 'Üstteki uyarıdan sistemi sıfırla.', warn: true },
};

interface Props {
  detection: Detection | null;
  status: PanelStatus;
  systemState?: SystemStatus['state'];
  minConfidence?: number;
  onSort: () => void;
  disabled?: boolean;
}

export function ResultCard({ detection, status, systemState, minConfidence, onSort, disabled }: Props) {
  const name = detection ? CLASSES[detection.label].name : '—';
  const confidence = detection?.confidence ?? 0;
  const blocked = status === 'uncertain' || status === 'bin_full';
  const canSort = status === 'ready' || blocked;
  const info = STATUS[status];

  let statusText = info.text;
  if (status === 'sorting' && systemState && systemState !== 'idle') statusText = `${STATE_TEXT[systemState]}…`;
  if (status === 'rejected' && detection?.operation) statusText = `Reddedildi · ${reasonText(detection.operation.reason)}`;

  return (
    <section className="card result">
      <span className="eyebrow">Son algılama</span>
      <h2 className="card__title">Sınıflandırma sonucu</h2>

      <div className="result__class">{name}</div>
      <div className="muted">{detection ? `${percent(confidence)} model güven skoru` : 'Tahmin yok'}</div>
      <div className="bar bar--thick">
        <div
          className={`bar__fill ${minConfidence !== undefined && confidence < minConfidence ? 'bar__fill--warn' : ''}`}
          style={{ width: `${confidence * 100}%` }}
        />
      </div>

      <dl className="rows">
        <div className="row">
          <dt>Hedef bölme</dt>
          <dd>{name}</dd>
        </div>
        <div className="row">
          <dt>İşlem durumu</dt>
          <dd className={info.warn ? 'text-warn' : undefined}>{statusText}</dd>
        </div>
      </dl>

      {info.hint && <p className="muted result__hint">{info.hint}</p>}

      <button className="btn-primary" onClick={onSort} disabled={disabled || !canSort}>
        {blocked ? 'Reddet ve kaydet' : 'Ayırmayı başlat'} <ArrowRight size={18} />
      </button>
    </section>
  );
}
