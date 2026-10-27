import { useEffect, useRef, useState } from 'react';
import { VideoOff } from 'lucide-react';
import { CLASSES, percent } from '../constants';
import type { Detection } from '../types';

type Tab = 'live' | 'detection';

export function Viewer({ detection }: { detection: Detection }) {
  const [tab, setTab] = useState<Tab>('detection');

  return (
    <section className="card viewer">
      <div className="card__head">
        <h2 className="card__title">Görüntüleme alanı</h2>
        <span className="muted">{tab === 'live' ? 'Anlık görüntü' : 'Algılama karesi'}</span>
      </div>

      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === 'live'} className="tab" onClick={() => setTab('live')}>
          Canlı kamera
        </button>
        <button role="tab" aria-selected={tab === 'detection'} className="tab" onClick={() => setTab('detection')}>
          Son algılama
        </button>
      </div>

      <div className="frame">
        {tab === 'live' ? <LiveCamera /> : <DetectionFrame detection={detection} />}
      </div>
    </section>
  );
}

function DetectionFrame({ detection }: { detection: Detection }) {
  const { label, confidence, box } = detection;
  const { name, Icon } = CLASSES[label];

  return (
    <>
      <div
        className="bbox"
        key={`${label}-${confidence}`}
        style={{ left: `${box.x}%`, top: `${box.y}%`, width: `${box.w}%`, height: `${box.h}%` }}
      >
        <span className="bbox__label">
          {name} · {percent(confidence)}
        </span>
        <Icon className="bbox__icon" size={24} strokeWidth={1.25} />
      </div>
      <span className="frame__caption">Örnek karar karesi · Şematik nesne temsili</span>
    </>
  );
}

// Şimdilik bilgisayar kamerası; ileride backend'deki kamera akışı (MJPEG) gelecek
function LiveCamera() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let stream: MediaStream | undefined;
    navigator.mediaDevices
      ?.getUserMedia({ video: true })
      .then((s) => {
        stream = s;
        if (videoRef.current) videoRef.current.srcObject = s;
      })
      .catch(() => setError(true));
    return () => stream?.getTracks().forEach((t) => t.stop());
  }, []);

  if (error || !navigator.mediaDevices) {
    return (
      <div className="frame__empty">
        <VideoOff size={28} strokeWidth={1.5} />
        <span>Kameraya erişilemedi</span>
      </div>
    );
  }

  return (
    <>
      <video ref={videoRef} className="frame__video" autoPlay playsInline muted />
      <span className="frame__live">
        <span className="dot" /> Canlı
      </span>
    </>
  );
}
