import { useCallback, useEffect, useRef, useState } from 'react';
import { Header, type Page } from './components/Header';
import { History } from './components/History';
import { Viewer } from './components/Viewer';
import { ResultCard } from './components/ResultCard';
import { BinCard } from './components/BinCard';
import { LastOperation } from './components/LastOperation';
import { ApiError, api } from './api';
import { CLASS_ORDER, FAULT_TEXT } from './constants';
import type { Bin, Detection, Operation, SortStatus, SystemStatus, WasteClass } from './types';

type Connection =
  | { state: 'connecting' }
  | { state: 'online'; classifier: string; hardware: string }
  | { state: 'offline' };

const statusFor = (d: Detection | null): SortStatus => (d ? (d.blockedReason ?? 'ready') : 'idle');
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function App() {
  const [page, setPage] = useState<Page>(pageFromHash);

  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  return (
    <>
      <Header page={page} />
      {page === 'history' ? <History /> : <Dashboard />}
    </>
  );
}

const pageFromHash = (): Page => (window.location.hash === '#/gecmis' ? 'history' : 'panel');

function Dashboard() {
  const [connection, setConnection] = useState<Connection>({ state: 'connecting' });
  const [bins, setBins] = useState<Record<WasteClass, number> | null>(null);
  const [detection, setDetection] = useState<Detection | null>(null);
  const [status, setStatus] = useState<SortStatus>('idle');
  const [lastOp, setLastOp] = useState<Operation | null>(null);
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  useEffect(() => () => void (mounted.current = false), []);

  const showDetection = (d: Detection | null) => {
    setDetection(d);
    setStatus(statusFor(d));
  };

  const updateBin = (bin: Bin) => setBins((prev) => prev && { ...prev, [bin.type]: bin.fill });

  const run = useCallback(async (fn: () => Promise<void>) => {
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Sunucuya bağlanılamadı');
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [health, binList, ops, sys] = await Promise.all([
          api.health(),
          api.bins(),
          api.operations({ limit: 1 }),
          api.system(),
        ]);
        setConnection({ state: 'online', classifier: health.classifier, hardware: health.hardware });
        setBins(Object.fromEntries(binList.map((b) => [b.type, b.fill])) as Record<WasteClass, number>);
        setLastOp(ops.items[0] ?? null);
        setSystem(sys);
        const latest = await api.latestDetection().catch(() => null);
        setDetection(latest);
        setStatus(sys.state === 'fault' ? 'fault' : statusFor(latest));
      } catch {
        setConnection({ state: 'offline' });
      }
    })();
  }, []);

  const handleUpload = (file: File) => run(async () => showDetection(await api.detect(file)));

  // Platformu döndürme ve atığı bırakma adımlarını sunucudaki kontrol servisi yürütür
  const handleSort = () =>
    run(async () => {
      if (!detection) return;
      const blocked = detection.blockedReason !== null;
      if (!blocked) setStatus('sorting');
      try {
        const [{ operation, bin }] = await Promise.all([api.sort(detection.id), wait(blocked ? 0 : 1200)]);
        updateBin(bin);
        setLastOp(operation);
        if (operation.status === 'failed') {
          // Kontrol servisi güvenli durdurmaya geçti; sıfırlanana kadar beklenir
          setStatus('fault');
          setSystem(await api.system());
          return;
        }
        if (!blocked) setStatus('done');
      } catch (e) {
        if (e instanceof ApiError && e.code === 'faulted') {
          setStatus('fault');
          setSystem(await api.system());
          return;
        }
        setStatus(statusFor(detection));
        throw e;
      }
      await wait(blocked ? 0 : 1400);
      if (!mounted.current) return;
      // Sıradaki atık: kameradan yeni kare
      showDetection(await api.detect().catch(() => null));
    });

  const handleReset = () =>
    run(async () => {
      setSystem(await api.resetSystem());
      // Atık hâlâ platformda; kamera onu yeniden değerlendirir
      showDetection(await api.detect().catch(() => null));
    });

  const handleEmpty = (type: WasteClass) =>
    run(async () => {
      updateBin(await api.emptyBin(type));
      if (detection?.label === type) showDetection(await api.latestDetection());
    });

  return (
    <main className="container">
        <section className="hero">
          <div>
            <span className="eyebrow">Daha temiz bir gelecek için</span>
            <h1 className="hero__title">Dönüşüm burada başlar.</h1>
            <p className="muted hero__lead">Atığı tanı, doğru bölmeye yönlendir, süreci takip et.</p>
          </div>
          <ConnectionPill connection={connection} />
        </section>

        {connection.state === 'offline' && (
          <div className="alert">
            Sunucuya bağlanılamadı. Backend'i <code>cd backend &amp;&amp; .venv/bin/python run.py</code> ile başlatıp
            sayfayı yenile.
          </div>
        )}
        {system?.fault && (
          <div className="alert alert--fault">
            <span>
              <strong>Sistem durduruldu · {FAULT_TEXT[system.fault.code] ?? system.fault.code}.</strong>{' '}
              {system.fault.message}. Sorunu giderdikten sonra sistemi sıfırla.
            </span>
            <button className="btn-small" onClick={handleReset}>
              Sistemi sıfırla
            </button>
          </div>
        )}
        {error && <div className="alert">{error}</div>}

        <div className="grid-main">
          <Viewer detection={detection} onUpload={handleUpload} />
          <ResultCard detection={detection} status={status} onSort={handleSort} />
        </div>

        <div className="section-head">
          <h2 className="card__title">Bölmelerin doluluk durumu</h2>
          <span className="muted">
            {connection.state === 'online' && connection.hardware !== 'simulated'
              ? 'Mesafe sensörleri'
              : 'Simüle edilmiş sensörler'}
          </span>
        </div>
        <div className="grid-bins">
          {CLASS_ORDER.map((type) => (
            <BinCard
              key={type}
              type={type}
              fill={bins?.[type] ?? 0}
              active={status === 'sorting' && detection?.label === type}
              onEmpty={() => handleEmpty(type)}
            />
          ))}
        </div>

        <LastOperation operation={lastOp} />
    </main>
  );
}

function ConnectionPill({ connection }: { connection: Connection }) {
  if (connection.state === 'connecting') return <span className="pill">Bağlanıyor…</span>;
  if (connection.state === 'offline') return <span className="pill pill--warn">Sunucu çevrimdışı</span>;
  const model = connection.classifier === 'yolo' ? 'YOLOv8 modeli' : 'Örnek sınıflandırıcı';
  const hardware = connection.hardware === 'simulated' ? 'Simülasyon' : 'Donanım';
  return (
    <span className="pill">
      <span className="dot" /> {model} · {hardware}
    </span>
  );
}
