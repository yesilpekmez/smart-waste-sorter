import { ArrowRight } from 'lucide-react';
import { CLASSES, MIN_CONFIDENCE, percent } from '../constants';
import type { Detection, SortStatus } from '../types';

const STATUS_TEXT: Record<SortStatus, string> = {
  ready: 'Ayırmaya hazır',
  sorting: 'Ayrılıyor…',
  done: 'Ayrıldı',
  bin_full: 'Bölme dolu',
  uncertain: 'Tahmin belirsiz',
};

interface Props {
  detection: Detection;
  status: SortStatus;
  onSort: () => void;
}

export function ResultCard({ detection, status, onSort }: Props) {
  const name = CLASSES[detection.label].name;
  const blocked = status === 'bin_full' || status === 'uncertain';

  return (
    <section className="card result">
      <span className="eyebrow">Son algılama</span>
      <h2 className="card__title">Sınıflandırma sonucu</h2>

      <div className="result__class">{name}</div>
      <div className="muted">{percent(detection.confidence)} model güven skoru</div>
      <div className="bar bar--thick">
        <div
          className={`bar__fill ${detection.confidence < MIN_CONFIDENCE ? 'bar__fill--warn' : ''}`}
          style={{ width: `${detection.confidence * 100}%` }}
        />
      </div>

      <dl className="rows">
        <div className="row">
          <dt>Hedef bölme</dt>
          <dd>{name}</dd>
        </div>
        <div className="row">
          <dt>İşlem durumu</dt>
          <dd className={blocked ? 'text-warn' : undefined}>{STATUS_TEXT[status]}</dd>
        </div>
      </dl>

      <button className="btn-primary" onClick={onSort} disabled={status === 'sorting'}>
        {blocked ? 'Sonraki atığa geç' : 'Ayırmayı simüle et'} <ArrowRight size={18} />
      </button>
    </section>
  );
}
