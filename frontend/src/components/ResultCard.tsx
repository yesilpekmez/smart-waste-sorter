import { ArrowRight } from 'lucide-react';
import { CLASSES, MIN_CONFIDENCE, percent } from '../constants';
import type { Detection, SortStatus } from '../types';

const STATUS_TEXT: Record<SortStatus, string> = {
  idle: 'Atık bekleniyor',
  ready: 'Ayırmaya hazır',
  sorting: 'Ayrılıyor…',
  done: 'Ayrıldı',
  bin_full: 'Bölme dolu',
  uncertain: 'Tahmin belirsiz',
  fault: 'Arıza · Sistem durdu',
};

interface Props {
  detection: Detection | null;
  status: SortStatus;
  onSort: () => void;
}

export function ResultCard({ detection, status, onSort }: Props) {
  const name = detection ? CLASSES[detection.label].name : '—';
  const confidence = detection?.confidence ?? 0;
  const blocked = status === 'bin_full' || status === 'uncertain';
  const disabled = !detection || status === 'sorting' || status === 'done' || status === 'fault';

  return (
    <section className="card result">
      <span className="eyebrow">Son algılama</span>
      <h2 className="card__title">Sınıflandırma sonucu</h2>

      <div className="result__class">{name}</div>
      <div className="muted">{detection ? `${percent(confidence)} model güven skoru` : 'Tahmin yok'}</div>
      <div className="bar bar--thick">
        <div
          className={`bar__fill ${confidence < MIN_CONFIDENCE ? 'bar__fill--warn' : ''}`}
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
          <dd className={blocked || status === 'fault' ? 'text-warn' : undefined}>{STATUS_TEXT[status]}</dd>
        </div>
      </dl>

      <button className="btn-primary" onClick={onSort} disabled={disabled}>
        {blocked ? 'Reddet ve sonrakine geç' : 'Ayırmayı başlat'} <ArrowRight size={18} />
      </button>
    </section>
  );
}
