import { CLASSES, percent } from '../constants';
import type { Operation } from '../types';

const REJECT_TEXT = { uncertain: 'Durduruldu · Belirsiz tahmin', bin_full: 'Durduruldu · Bölme dolu' };

export function LastOperation({ operation }: { operation: Operation | null }) {
  return (
    <section className="card">
      <div className="card__head card__head--divided">
        <h2 className="card__title">Son işlem</h2>
        {operation && (
          <span className="muted">
            {new Date(operation.createdAt).toLocaleTimeString('tr-TR', {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })}
          </span>
        )}
      </div>
      <div className="op">
        {operation ? (
          <>
            <span>
              {CLASSES[operation.label].name} · {percent(operation.confidence)} güven
            </span>
            {operation.status === 'completed' ? (
              <span className="badge">Ayırma tamamlandı</span>
            ) : (
              <span className="badge badge--warn">{operation.reason ? REJECT_TEXT[operation.reason] : 'Durduruldu'}</span>
            )}
          </>
        ) : (
          <span className="muted">Henüz işlem yok</span>
        )}
      </div>
    </section>
  );
}
