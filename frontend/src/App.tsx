import { useEffect, useRef, useState } from 'react';
import { Header } from './components/Header';
import { Viewer } from './components/Viewer';
import { ResultCard } from './components/ResultCard';
import { BinCard } from './components/BinCard';
import { LastOperation } from './components/LastOperation';
import { CLASS_ORDER, FULL_THRESHOLD, MIN_CONFIDENCE } from './constants';
import { initialDetection, initialFill, initialOperation, randomDetection } from './mock';
import type { Detection, Operation, SortStatus, WasteClass } from './types';

function statusFor(detection: Detection, fill: Record<WasteClass, number>): SortStatus {
  if (detection.confidence < MIN_CONFIDENCE) return 'uncertain';
  if (fill[detection.label] >= FULL_THRESHOLD) return 'bin_full';
  return 'ready';
}

export default function App() {
  const [fill, setFill] = useState(initialFill);
  const [detection, setDetection] = useState(initialDetection);
  const [status, setStatus] = useState<SortStatus>(() => statusFor(initialDetection, initialFill));
  const [lastOp, setLastOp] = useState<Operation>(initialOperation);
  const timers = useRef<number[]>([]);

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const later = (fn: () => void, ms: number) => timers.current.push(window.setTimeout(fn, ms));

  const nextDetection = (currentFill: Record<WasteClass, number>) => {
    const d = randomDetection();
    setDetection(d);
    setStatus(statusFor(d, currentFill));
  };

  const record = (opStatus: Operation['status']) =>
    setLastOp((prev) => ({
      id: prev.id + 1,
      label: detection.label,
      confidence: detection.confidence,
      status: opStatus,
      time: new Date(),
    }));

  // Gerçek sistemde bu adımları kontrol servisi yürütecek: platform döner, servo atığı bırakır
  const handleSort = () => {
    if (status === 'uncertain' || status === 'bin_full') {
      record('rejected');
      nextDetection(fill);
      return;
    }
    setStatus('sorting');
    later(() => {
      const updated = { ...fill, [detection.label]: Math.min(100, fill[detection.label] + 3 + Math.round(Math.random() * 4)) };
      setFill(updated);
      setStatus('done');
      record('completed');
      later(() => nextDetection(updated), 1400);
    }, 1200);
  };

  const handleEmpty = (type: WasteClass) => {
    const updated = { ...fill, [type]: 0 };
    setFill(updated);
    if (status === 'bin_full' && detection.label === type) setStatus(statusFor(detection, updated));
  };

  return (
    <>
      <Header />
      <main className="container">
        <section className="hero">
          <div>
            <span className="eyebrow">Daha temiz bir gelecek için</span>
            <h1 className="hero__title">Dönüşüm burada başlar.</h1>
            <p className="muted hero__lead">Atığı tanı, doğru bölmeye yönlendir, süreci takip et.</p>
          </div>
          <span className="pill">Demo · Örnek veriler</span>
        </section>

        <div className="grid-main">
          <Viewer detection={detection} />
          <ResultCard detection={detection} status={status} onSort={handleSort} />
        </div>

        <div className="section-head">
          <h2 className="card__title">Bölmelerin doluluk durumu</h2>
          <span className="muted">Örnek sensör verileri</span>
        </div>
        <div className="grid-bins">
          {CLASS_ORDER.map((type) => (
            <BinCard
              key={type}
              type={type}
              fill={fill[type]}
              active={status === 'sorting' && detection.label === type}
              onEmpty={() => handleEmpty(type)}
            />
          ))}
        </div>

        <LastOperation operation={lastOp} />
      </main>
    </>
  );
}
