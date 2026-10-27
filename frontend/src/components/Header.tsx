import { Recycle } from 'lucide-react';

export type Page = 'panel' | 'history';

const LINKS: { page: Page; href: string; label: string }[] = [
  { page: 'panel', href: '#/', label: 'Panel' },
  { page: 'history', href: '#/gecmis', label: 'İşlem geçmişi' },
];

export function Header({ page }: { page: Page }) {
  return (
    <header className="header">
      <div className="header__inner">
        <a className="brand" href="#/">
          <div className="brand__logo">
            <Recycle size={22} strokeWidth={1.75} />
          </div>
          <div>
            <div className="brand__name">ayır.</div>
            <div className="brand__tagline">Akıllı geri dönüşüm</div>
          </div>
        </a>
        <nav className="nav">
          {LINKS.map((l) => (
            <a key={l.page} href={l.href} className="nav__link" aria-current={page === l.page ? 'page' : undefined}>
              {l.label}
            </a>
          ))}
        </nav>
      </div>
    </header>
  );
}
