import { useCallback, useEffect, useRef, useState } from 'react';
import { Viewer } from './Viewer';
import { ResultCard, type PanelStatus } from './ResultCard';
import { BinCard } from './BinCard';
import { LastOperation } from './LastOperation';
import { ApiError, NetworkError, api } from '../api';
import { CLASS_ORDER, formatTime, reasonText } from '../constants';
import type { Detection, Health, Operation, SystemStatus, WasteClass } from '../types';

const POLL_MS = 3000;

type Connection = 'connecting' | 'online' | 'offline';

interface Snapshot {
  system: SystemStatus;
  bins: Record<WasteClass, number>;
  detection: Detection | null;
  lastOp: Operation | null;
  at: Date;
}

// Panel durumu yalnızca sunucudan gelen verilerden türetilir
function panelStatus(snapshot: Snapshot | null, sorting: boolean): PanelStatus {
  if (!snapshot) return 'idle';
  const { system, detection } = snapshot;
  if (system.state === 'fault') return 'fault';
  if (sorting || system.runningOperationId !== null) return 'sorting';
  if (!detection) return 'idle';

  const op = detection.operation;
  if (op) {
    if (op.status === 'completed') return 'done';
    if (op.status === 'rejected') return 'rejected';
    if (op.status === 'aborted') return 'aborted';
    if (op.status === 'failed') return 'recovered'; // arıza giderildi, atık yeniden analiz edilmeli
    return 'sorting';
  }
  if (!detection.sortable) return 'stale';
  return detection.blockedReason ?? 'ready';
}

export function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [connection, setConnection] = useState<Connection>('connecting');
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [sorting, setSorting] = useState(false);
  const [busy, setBusy] = useState(false); // analiz ya da sıfırlama sürüyor
  const [error, setError] = useState<string | null>(null);
  const needsHealth = useRef(true);

  const refresh = useCallback(async () => {
    try {
      if (needsHealth.current) {
        setHealth(await api.health());
        needsHealth.current = false;
      }
      const [system, binList, detection, ops] = await Promise.all([
        api.system(),
        api.bins(),
        api.latestDetection(),
        api.operations({ limit: 1 }),
      ]);
      setSnapshot({
        system,
        bins: Object.fromEntries(binList.map((b) => [b.type, b.fill])) as Record<WasteClass, number>,
        detection,
        lastOp: ops.items[0] ?? null,
        at: new Date(),
      });
      setConnection('online');
    } catch (e) {
      if (!(e instanceof NetworkError)) throw e;
      // Sunucuya ulaşılamıyor; yeniden bağlanınca ayarlar tekrar alınır
      setConnection('offline');
      needsHealth.current = true;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    const tick = async () => {
      await refresh().catch(() => undefined);
      if (!cancelled) timer = window.setTimeout(tick, POLL_MS);
    };
    tick();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [refresh]);

  const run = async (fn: () => Promise<unknown>) => {
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Sunucuya bağlanılamadı');
    } finally {
      await refresh().catch(() => undefined);
    }
  };

  const handleAnalyze = (image: File) =>
    run(async () => {
      setBusy(true);
      try {
        await api.detect(image);
      } finally {
        setBusy(false);
      }
    });

  const handleSort = () =>
    run(async () => {
      const detection = snapshot?.detection;
      if (!detection) return;
      setSorting(true);
      try {
        await api.sort(detection.id);
      } finally {
        setSorting(false);
      }
    });

  const handleReset = () =>
    run(async () => {
      setBusy(true);
      try {
        await api.resetSystem();
      } finally {
        setBusy(false);
      }
    });

  const handleEmpty = (type: WasteClass) => run(() => api.emptyBin(type));

  const status = panelStatus(snapshot, sorting);
  const detection = snapshot?.detection ?? null;
  const system = snapshot?.system;
  const simulated = health?.hardware === 'simulated';

  return (
    <main className="container">
      <section className="hero">
        <div>
          <span className="eyebrow">Daha temiz bir gelecek için</span>
          <h1 className="hero__title">Dönüşüm burada başlar.</h1>
          <p className="muted hero__lead">Atığı tanı, doğru bölmeye yönlendir, süreci takip et.</p>
        </div>
        <ConnectionPill connection={connection} health={health} />
      </section>

      {connection === 'offline' && (
        <div className="alert">
          Sunucuya bağlanılamıyor; yeniden deneniyor. Backend'i{' '}
          <code>cd backend &amp;&amp; .venv/bin/python run.py</code> ile başlat.
          {snapshot && ` Gösterilen veriler ${formatTime(snapshot.at.toISOString())} itibarıyla.`}
        </div>
      )}
      {system?.fault && (
        <div className="alert alert--fault">
          <span>
            <strong>Sistem durduruldu · {reasonText(system.fault.code)}.</strong> {system.fault.message}. Sorunu
            giderdikten sonra sistemi sıfırla.
          </span>
          <button className="btn-small" onClick={handleReset} disabled={busy || connection !== 'online'}>
            {busy ? 'Sıfırlanıyor…' : 'Sistemi sıfırla'}
          </button>
        </div>
      )}
      {error && <div className="alert">{error}</div>}

      <div className="grid-main">
        <Viewer
          detection={detection}
          onAnalyze={handleAnalyze}
          analyzing={busy}
          canAnalyze={connection === 'online' && status !== 'sorting' && status !== 'fault'}
        />
        <ResultCard
          detection={detection}
          status={status}
          systemState={system?.state}
          minConfidence={health?.minConfidence}
          onSort={handleSort}
        />
      </div>

      <div className="section-head">
        <h2 className="card__title">Bölmelerin doluluk durumu</h2>
        <span className="muted">
          Yaklaşık · {simulated ? 'simüle edilmiş sensörler' : 'mesafe sensörleri'}
          {snapshot && ` · ${formatTime(snapshot.at.toISOString())}`}
        </span>
      </div>
      <div className="grid-bins">
        {CLASS_ORDER.map((type) => (
          <BinCard
            key={type}
            type={type}
            fill={snapshot ? snapshot.bins[type] : null}
            fullThreshold={health?.fullThreshold}
            active={status === 'sorting' && detection?.label === type}
            onEmpty={simulated ? () => handleEmpty(type) : undefined}
          />
        ))}
      </div>

      <LastOperation operation={snapshot?.lastOp ?? null} />
    </main>
  );
}

function ConnectionPill({ connection, health }: { connection: Connection; health: Health | null }) {
  if (connection === 'connecting') return <span className="pill">Bağlanıyor…</span>;
  if (connection === 'offline') return <span className="pill pill--warn">Sunucu çevrimdışı</span>;
  const model = health?.classifier === 'yolo' ? `YOLOv8 · ${health.modelVersion}` : 'Örnek sınıflandırıcı';
  const hardware = health?.hardware === 'simulated' ? 'Simülasyon' : 'Donanım';
  return (
    <span className="pill" title={`Güven eşiği ${health?.minConfidence} · Dolu eşiği %${health?.fullThreshold}`}>
      <span className="dot" /> {model} · {hardware}
    </span>
  );
}
