import { Recycle } from 'lucide-react';

export function Header() {
  return (
    <header className="header">
      <div className="header__inner">
        <div className="brand">
          <div className="brand__logo">
            <Recycle size={22} strokeWidth={1.75} />
          </div>
          <div>
            <div className="brand__name">ayır.</div>
            <div className="brand__tagline">Akıllı geri dönüşüm</div>
          </div>
        </div>
      </div>
    </header>
  );
}
