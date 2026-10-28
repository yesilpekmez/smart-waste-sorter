import { useEffect, useRef, useState } from 'react';
import { ImageOff, X } from 'lucide-react';
import { api } from '../api';
import { CLASSES, CLASS_ORDER, STATE_TEXT, operationText, percent } from '../constants';
import type { Operation, Stats } from '../types';

const PAGE_SIZE = 20;

const STATUS_FILTERS = [
  { value: '', label: 'Tümü' },
  { value: 'completed', label: 'Ayrılan' },
  { value: 'rejected', label: 'Reddedilen' },
  { value: 'aborted', label: 'Başlatılamayan' },
  { value: 'failed', label: 'Arıza' },
];

const formatDateTime = (iso: string) => {
  const d = new Date(iso);
  return `${d.toLocaleDateString('tr-TR', { day: '2-digit', month: 'short' })} ${d.toLocaleTimeString('tr-TR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })}`;
};

export function History() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [label, setLabel] = useState('');
  const [status, setStatus] = useState('');
  const [items, setItems] = useState<Operation[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [selected, setSelected] = useState<Operation | null>(null);
  // Hızlı filtre değişiminde eski isteğin yanıtı yenisini ezmesin
  const requestId = useRef(0);

  useEffect(() => {
    api.stats().then(setStats).catch(() => setError(true));
  }, []);

  useEffect(() => {
    const id = ++requestId.current;
    setLoading(true);
    api
      .operations({ label, status, limit: PAGE_SIZE })
      .then((res) => {
        if (id !== requestId.current) return;
        setItems(res.items);
        setTotal(res.total);
        setError(false);
      })
      .catch(() => id === requestId.current && setError(true))
      .finally(() => id === requestId.current && setLoading(false));
  }, [label, status]);

  const loadMore = async () => {
    const id = ++requestId.current;
    setLoading(true);
    const res = await api.operations({ label, status, limit: PAGE_SIZE, offset: items.length }).catch(() => null);
    if (id !== requestId.current) return;
    if (res) setItems((prev) => [...prev, ...res.items]);
    else setError(true);
    setLoading(false);
  };

  return (
    <main className="container">
      <section className="hero">
        <div>
          <span className="eyebrow">Kayıtlar</span>
          <h1 className="hero__title">İşlem geçmişi.</h1>
          <p className="muted hero__lead">Sistemin verdiği her kararı ve sonucunu buradan izle.</p>
        </div>
      </section>

      {error && <div className="alert">Sunucuya bağlanılamadı.</div>}

      <div className="grid-bins">
        <StatTile label="Toplam işlem" value={stats ? String(stats.total) : '—'} />
        <StatTile
          label="Başarılı ayırma"
          value={stats?.successRate != null ? percent(stats.successRate) : '—'}
          note={
            stats
              ? `${stats.completed} işlem${stats.averageDurationMs ? ` · ort. ${(stats.averageDurationMs / 1000).toFixed(1)} sn` : ''}`
              : undefined
          }
        />
        <StatTile
          label="Ortalama güven"
          value={stats?.averageConfidence != null ? percent(stats.averageConfidence) : '—'}
        />
        <StatTile
          label="Reddedilen / arıza"
          value={stats ? `${stats.rejected} / ${stats.failed}` : '—'}
          note={stats?.aborted ? `${stats.aborted} başlatılamadı` : undefined}
          warn={!!stats && stats.failed > 0}
        />
      </div>

      <section className="card">
        <div className="filters">
          <div className="chips" role="group" aria-label="Atık türü">
            <Chip active={label === ''} onClick={() => setLabel('')}>
              Tüm atıklar
            </Chip>
            {CLASS_ORDER.map((c) => (
              <Chip key={c} active={label === c} onClick={() => setLabel(c)}>
                {CLASSES[c].name}
              </Chip>
            ))}
          </div>
          <div className="chips" role="group" aria-label="Durum">
            {STATUS_FILTERS.map((f) => (
              <Chip key={f.value} active={status === f.value} onClick={() => setStatus(f.value)}>
                {f.label}
              </Chip>
            ))}
          </div>
        </div>

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Kare</th>
                <th>Atık</th>
                <th>Güven</th>
                <th>Sonuç</th>
                <th className="table__time">Zaman</th>
              </tr>
            </thead>
            <tbody>
              {items.map((op) => (
                <OperationRow key={op.id} op={op} onOpen={() => setSelected(op)} />
              ))}
            </tbody>
          </table>
          {!loading && items.length === 0 && <p className="muted table__empty">Bu filtrelere uyan işlem yok.</p>}
        </div>

        <div className="table__footer">
          <span className="muted">
            {items.length} / {total} işlem
          </span>
          {items.length < total && (
            <button className="tab" onClick={loadMore} disabled={loading}>
              {loading ? 'Yükleniyor…' : 'Daha fazla göster'}
            </button>
          )}
        </div>
      </section>

      {selected && <OperationDialog op={selected} onClose={() => setSelected(null)} />}
    </main>
  );
}

function OperationRow({ op, onOpen }: { op: Operation; onOpen: () => void }) {
  const { name, Icon } = CLASSES[op.label];
  return (
    <tr className="table__row" onClick={onOpen} tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && onOpen()}>
      <td>
        {op.imageUrl ? (
          <img className="thumb" src={op.imageUrl} alt={name} loading="lazy" />
        ) : (
          <span className="thumb thumb--empty" title="Kamera karesi kaydedilmedi">
            <ImageOff size={16} strokeWidth={1.5} />
          </span>
        )}
      </td>
      <td>
        <span className="cell-class">
          <Icon size={16} strokeWidth={1.5} /> {name}
        </span>
      </td>
      <td>{percent(op.confidence)}</td>
      <td>
        <span className={`badge ${op.status === 'completed' ? '' : 'badge--warn'}`}>{operationText(op)}</span>
      </td>
      <td className="table__time muted">{formatDateTime(op.createdAt)}</td>
    </tr>
  );
}

function OperationDialog({ op, onClose }: { op: Operation; onClose: () => void }) {
  const { name } = CLASSES[op.label];

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="dialog__backdrop" onClick={onClose}>
      <div
        className="dialog card"
        role="dialog"
        aria-modal="true"
        aria-label={`İşlem #${op.id}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="card__head">
          <h2 className="card__title">
            İşlem #{op.id} · {name}
          </h2>
          <button className="dialog__close" onClick={onClose} aria-label="Kapat">
            <X size={20} />
          </button>
        </div>

        <div className="dialog__body">
          {op.imageUrl ? (
            <img className="dialog__image" src={op.imageUrl} alt={`Algılanan atık: ${name}`} />
          ) : (
            <div className="dialog__image thumb--empty">
              <ImageOff size={28} strokeWidth={1.5} />
            </div>
          )}

          <dl className="rows rows--compact">
            <Row label="Sonuç" value={operationText(op)} warn={op.status !== 'completed'} />
            {op.message && <Row label="Ayrıntı" value={op.message} />}
            <Row label="Tahmin" value={`${name} · ${percent(op.confidence)}`} />
            <Row label="Model" value={op.modelVersion} />
            <Row label="Eşikler" value={`Güven ≥ ${op.minConfidence} · Dolu ≥ %${op.fullThreshold}`} />
            <Row label="Başlangıç" value={formatDateTime(op.createdAt)} />
            {op.durationMs !== null && <Row label="Süre" value={`${(op.durationMs / 1000).toFixed(2)} sn`} />}
          </dl>
        </div>

        {op.trace.length > 0 && (
          <>
            <h3 className="dialog__subtitle">Aşamalar · başlangıçtan itibaren</h3>
            <ol className="trace">
              {op.trace.map(([state, t], i) => (
                <li key={i} className={state === 'fault' ? 'text-warn' : undefined}>
                  <span>{STATE_TEXT[state] ?? state}</span>
                  <span className="muted">{t.toFixed(2)} sn</span>
                </li>
              ))}
            </ol>
          </>
        )}
      </div>
    </div>
  );
}

function Row({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className="row">
      <dt>{label}</dt>
      <dd className={warn ? 'text-warn' : undefined}>{value}</dd>
    </div>
  );
}

function StatTile({ label, value, note, warn }: { label: string; value: string; note?: string; warn?: boolean }) {
  return (
    <div className="card bin">
      <div className="bin__head">{label}</div>
      <div className={`bin__value ${warn ? 'text-warn' : ''}`}>{value}</div>
      {note && <div className="muted">{note}</div>}
    </div>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button className="chip" aria-pressed={active} onClick={onClick}>
      {children}
    </button>
  );
}
