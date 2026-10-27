import { useEffect, useState } from 'react';
import { ImageOff } from 'lucide-react';
import { api } from '../api';
import { CLASSES, CLASS_ORDER, FAULT_TEXT, percent } from '../constants';
import type { Operation, Stats } from '../types';

const PAGE_SIZE = 20;

const STATUS_FILTERS = [
  { value: '', label: 'Tümü' },
  { value: 'completed', label: 'Tamamlanan' },
  { value: 'rejected', label: 'Durdurulan' },
  { value: 'failed', label: 'Arıza' },
];

const REASON_TEXT: Record<string, string> = {
  uncertain: 'Belirsiz tahmin',
  bin_full: 'Bölme dolu',
  ...FAULT_TEXT,
};

export function History() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [label, setLabel] = useState('');
  const [status, setStatus] = useState('');
  const [items, setItems] = useState<Operation[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.stats().then(setStats).catch(() => setError(true));
  }, []);

  useEffect(() => {
    setLoading(true);
    api
      .operations({ label, status, limit: PAGE_SIZE })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [label, status]);

  const loadMore = async () => {
    setLoading(true);
    const res = await api.operations({ label, status, limit: PAGE_SIZE, offset: items.length }).catch(() => null);
    if (res) setItems((prev) => [...prev, ...res.items]);
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
          note={stats ? `${stats.completed} işlem` : undefined}
        />
        <StatTile
          label="Ortalama güven"
          value={stats?.averageConfidence != null ? percent(stats.averageConfidence) : '—'}
        />
        <StatTile
          label="Durdurulan / arıza"
          value={stats ? `${stats.rejected} / ${stats.failed}` : '—'}
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
                <OperationRow key={op.id} op={op} />
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
    </main>
  );
}

function OperationRow({ op }: { op: Operation }) {
  const { name, Icon } = CLASSES[op.label];
  const time = new Date(op.createdAt);
  return (
    <tr>
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
        {op.status === 'completed' ? (
          <span className="badge">Ayrıldı</span>
        ) : (
          <span className="badge badge--warn">
            {op.status === 'failed' ? 'Arıza' : 'Durduruldu'} · {REASON_TEXT[op.reason ?? ''] ?? op.reason}
          </span>
        )}
      </td>
      <td className="table__time muted">
        {time.toLocaleDateString('tr-TR', { day: '2-digit', month: 'short' })}{' '}
        {time.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
      </td>
    </tr>
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
