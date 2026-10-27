import { useEffect, useRef, useState } from 'react';
import { ImageUp, ScanSearch, VideoOff } from 'lucide-react';
import { CLASSES, percent } from '../constants';
import type { Detection } from '../types';

type Tab = 'live' | 'detection';

interface Props {
  detection: Detection | null;
  onUpload: (file: File) => Promise<void>;
}

export function Viewer({ detection, onUpload }: Props) {
  const [tab, setTab] = useState<Tab>('detection');
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File | undefined) => {
    if (!file) return;
    setUploading(true);
    setTab('detection');
    await onUpload(file);
    setUploading(false);
    if (inputRef.current) inputRef.current.value = '';
  };

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
        <button className="tab tab--action" onClick={() => inputRef.current?.click()} disabled={uploading}>
          <ImageUp size={18} strokeWidth={1.75} /> {uploading ? 'Analiz ediliyor…' : 'Fotoğraf yükle'}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>

      <div className="frame">
        {tab === 'live' ? <LiveCamera /> : <DetectionFrame detection={detection} />}
      </div>
    </section>
  );
}

function DetectionFrame({ detection }: { detection: Detection | null }) {
  if (!detection) {
    return (
      <div className="frame__empty">
        <ScanSearch size={28} strokeWidth={1.5} />
        <span>Henüz algılama yok · Bir fotoğraf yükleyerek başla</span>
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
      <span className="frame__caption">Kamera karesi · Şematik nesne temsili</span>
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
