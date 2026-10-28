import { useEffect, useState } from 'react';
import { Header, type Page } from './components/Header';
import { Dashboard } from './components/Dashboard';
import { History } from './components/History';

const pageFromHash = (): Page => (window.location.hash === '#/gecmis' ? 'history' : 'panel');

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
