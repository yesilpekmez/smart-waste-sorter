import { CLASSES, formatTime, operationText, percent } from '../constants';
import type { Operation } from '../types';

export function LastOperation({ operation }: { operation: Operation | null }) {
  return (
    <section className="card">
      <div className="card__head card__head--divided">
        <h2 className="card__title">Son işlem</h2>
        {operation && (
          <span className="muted">
            {operation.durationMs !== null && `${(operation.durationMs / 1000).toFixed(1)} sn · `}
            {formatTime(operation.createdAt)}
          </span>
        )}
      </div>
      <div className="op">
        {operation ? (
          <>
            <span>
              {CLASSES[operation.label].name} · {percent(operation.confidence)} güven
            </span>
            <span className={`badge ${operation.status === 'completed' ? '' : 'badge--warn'}`}>
              {operationText(operation)}
            </span>
          </>
        ) : (
          <span className="muted">Henüz işlem yok</span>
        )}
      </div>
    </section>
  );
}
