import { useEffect, useRef, useState } from 'react';
import { Camera, ImageUp, ScanSearch, VideoOff } from 'lucide-react';
import { CLASSES, percent } from '../constants';
import type { Detection } from '../types';

type Tab = 'live' | 'detection';

interface Props {
  detection: Detection | null;
  onAnalyze: (image: File) => Promise<void>;
  analyzing: boolean;
  canAnalyze: boolean;
}

export function Viewer({ detection, onAnalyze, analyzing, canAnalyze }: Props) {
  const [tab, setTab] = useState<Tab>('detection');
  const inputRef = useRef<HTMLInputElement>(null);

  const analyze = async (file: File) => {
    await onAnalyze(file);
    setTab('detection');
  };

  return (
    <section className="card viewer">
      <div className="card__head">
        <h2 className="card__title">Görüntüleme alanı</h2>
        <span className="muted">{tab === 'live' ? 'Anlık görüntü' : 'Modelin karar verdiği kare'}</span>
      </div>

      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === 'live'} className="tab" onClick={() => setTab('live')}>
          Canlı kamera
        </button>
        <button role="tab" aria-selected={tab === 'detection'} className="tab" onClick={() => setTab('detection')}>
          Son algılama
        </button>
        <button
          className="tab tab--action"
          onClick={() => inputRef.current?.click()}
          disabled={analyzing || !canAnalyze}
        >
          <ImageUp size={18} strokeWidth={1.75} /> {analyzing ? 'Analiz ediliyor…' : 'Fotoğraf yükle'}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = '';
            if (file) analyze(file);
          }}
        />
      </div>

      <div className="frame">
        {tab === 'live' ? (
          <LiveCamera onCapture={analyze} disabled={analyzing || !canAnalyze} analyzing={analyzing} />
        ) : (
          <DetectionFrame detection={detection} />
        )}
      </div>
    </section>
  );
}

function DetectionFrame({ detection }: { detection: Detection | null }) {
  if (!detection) {
    return (
      <div className="frame__empty">
        <ScanSearch size={28} strokeWidth={1.5} />
        <span>Henüz algılama yok · Kameradan kare al ya da fotoğraf yükle</span>
      </div>
    );
  }

  const { label, confidence, box, imageUrl } = detection;
  const { name, Icon } = CLASSES[label];
  const text = `${name} · ${percent(confidence)}`;

  const boxEl = box ? (
    <div
      className="bbox"
      key={detection.id}
      style={{ left: `${box.x}%`, top: `${box.y}%`, width: `${box.w}%`, height: `${box.h}%` }}
    >
      <span className="bbox__label">{text}</span>
      {!imageUrl && <Icon className="bbox__icon" size={24} strokeWidth={1.25} />}
    </div>
  ) : (
    // Sınıflandırma modeli konum vermez; etiket görüntünün köşesinde durur
    <span className="bbox__label bbox__label--corner" key={detection.id}>
      {text}
    </span>
  );

  if (imageUrl) {
    // Kutu yüzdeleri görüntüye göre olduğu için kutuyu görüntüyle aynı kaba koyuyoruz
    return (
      <div className="frame__photo">
        <div className="photo">
          <img src={imageUrl} alt={`Algılanan atık: ${name}`} />
          {boxEl}
        </div>
      </div>
    );
  }

  return (
    <>
      {boxEl}
      <span className="frame__caption">Örnek sınıflandırıcı · Şematik nesne temsili</span>
    </>
  );
}

// Şimdilik bilgisayar kamerası; Raspberry Pi'de backend'deki kamera kullanılacak
function LiveCamera({
  onCapture,
  disabled,
  analyzing,
}: {
  onCapture: (image: File) => void;
  disabled: boolean;
  analyzing: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [state, setState] = useState<'starting' | 'ready' | 'error'>('starting');

  useEffect(() => {
    let cancelled = false;
    let stream: MediaStream | undefined;

    if (!navigator.mediaDevices?.getUserMedia) {
      setState('error');
      return;
    }
    navigator.mediaDevices
      .getUserMedia({ video: true })
      .then((s) => {
        // Sekme, izin beklenirken kapandıysa akışı hemen kapat
        if (cancelled) {
          s.getTracks().forEach((t) => t.stop());
          return;
        }
        stream = s;
        if (videoRef.current) videoRef.current.srcObject = s;
        setState('ready');
      })
      .catch(() => !cancelled && setState('error'));

    return () => {
      cancelled = true;
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const capture = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')?.drawImage(video, 0, 0);
    // Modele gönderilen kare, sunucuda tahminle birlikte saklanır
    canvas.toBlob(
      (blob) => blob && onCapture(new File([blob], `kare-${Date.now()}.jpg`, { type: 'image/jpeg' })),
      'image/jpeg',
      0.92,
    );
  };

  if (state === 'error') {
    return (
      <div className="frame__empty">
        <VideoOff size={28} strokeWidth={1.5} />
        <span>Kameraya erişilemedi · Fotoğraf yükleyerek devam edebilirsin</span>
      </div>
    );
  }

  return (
    <>
      <video ref={videoRef} className="frame__video" autoPlay playsInline muted />
      <span className="frame__live">
        <span className="dot" /> {state === 'ready' ? 'Canlı' : 'Kamera açılıyor…'}
      </span>
      <button className="capture" onClick={capture} disabled={disabled || state !== 'ready'}>
        <Camera size={18} strokeWidth={1.75} /> {analyzing ? 'Analiz ediliyor…' : 'Kare al ve analiz et'}
      </button>
    </>
  );
}
