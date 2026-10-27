import { CLASSES, percent } from '../constants';
import type { Operation } from '../types';

export function LastOperation({ operation }: { operation: Operation }) {
  const ok = operation.status === 'completed';
  return (
    <section className="card">
      <div className="card__head card__head--divided">
        <h2 className="card__title">Son işlem</h2>
        <span className="muted">
          {operation.time.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </span>
      </div>
      <div className="op">
        <span>
          {CLASSES[operation.label].name} · {percent(operation.confidence)} güven
        </span>
        <span className={`badge ${ok ? '' : 'badge--warn'}`}>
          {ok ? 'Simülasyon tamamlandı' : 'Ayırma durduruldu'}
        </span>
      </div>
    </section>
  );
}
