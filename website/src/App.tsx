import { Component, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import {
  Activity,
  ArrowUpRight,
  BookOpen,
  ChartNoAxesCombined,
  ChevronRight,
  CircleHelp,
  Database,
  Download,
  FlaskConical,
  LayoutDashboard,
  LoaderCircle,
  Menu,
  Network,
  ShieldCheck,
  Waves,
  X,
} from 'lucide-react';
import type { DataBundle } from './lib/data';
import { download, loadData } from './lib/data';
import {
  About,
  Dataset,
  Demonstrator,
  Interpretation,
  Methodology,
  Models,
  Overview,
  Summary,
} from './pages';
import { Button } from './components/ui/button';
import { GROUP_NAME } from './lib/presentation';

const navigation = [
  { path: '/', label: 'Overview', icon: LayoutDashboard },
  { path: '/dataset', label: 'Dataset explorer', icon: Database },
  { path: '/models', label: 'Models & results', icon: ChartNoAxesCombined },
  { path: '/predict', label: 'Prediction demo', icon: FlaskConical },
  { path: '/interpretation', label: 'Model interpretation', icon: Network },
  { path: '/methodology', label: 'Methodology', icon: BookOpen },
  { path: '/summary', label: 'Research summary', icon: Activity },
  { path: '/about', label: 'About & sources', icon: CircleHelp },
];

class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div className="error-page">
        <h1>This view could not be displayed.</h1>
        <p>No prediction or replacement data was generated. Reload to try again.</p>
        <Button onClick={() => location.reload()}>Reload website</Button>
      </div>
    ) : (
      this.props.children
    );
  }
}

export default function App() {
  const [data, setData] = useState<DataBundle | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const current = navigation.find((n) => n.path === location.pathname);
  useEffect(() => {
    const abort = new AbortController();
    setError('');
    loadData(abort.signal)
      .then(setData)
      .catch((e) => {
        if (!abort.signal.aborted)
          setError(e instanceof Error ? e.message : 'Research data unavailable.');
      });
    return () => abort.abort();
  }, [attempt]);
  useEffect(() => {
    setOpen(false);
    window.scrollTo({ top: 0, behavior: 'instant' });
    document.title = `${current?.label || 'Not found'} | ${GROUP_NAME} | Undersea Research`;
    document.getElementById('main-content')?.focus();
  }, [location.pathname, current?.label]);
  useEffect(() => {
    if (!open) return;
    const sidebar = document.getElementById('site-navigation');
    const links = sidebar?.querySelectorAll<HTMLElement>('a[href],button:not([disabled])');
    links?.[0]?.focus();
    const listener = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        document.getElementById('menu-toggle')?.focus();
      }
      if (e.key === 'Tab' && links?.length) {
        const first = links[0],
          last = links[links.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener('keydown', listener);
    return () => document.removeEventListener('keydown', listener);
  }, [open]);
  return (
    <ErrorBoundary>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <div className="app-shell">
        {open && (
          <button
            className="sidebar-backdrop"
            aria-label="Close navigation"
            onClick={() => setOpen(false)}
          />
        )}
        <aside className={`sidebar ${open ? 'is-open' : ''}`} id="site-navigation">
          <Link to="/" className="brand" aria-label="Undersea Research home">
            <span className="brand-mark">
              <Waves size={26} />
            </span>
            <span>
              UNDERSEA<span>RESEARCH ANALYTICS</span>
            </span>
          </Link>
          <div className="sidebar-label">RESEARCH WORKSPACE</div>
          <nav aria-label="Main navigation">
            {navigation.map(({ path, label, icon: Icon }) => (
              <NavLink key={path} to={path} end={path === '/'}>
                <Icon size={18} />
                <span>{label}</span>
                <ChevronRight size={14} className="nav-chevron" />
              </NavLink>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="sidebar-note">
              <ShieldCheck size={18} />
              <div>
                <strong>Academic demonstration</strong>
                <p>
                  Synthetic research dataset.
                  <br />
                  Not a live fault alert service.
                </p>
              </div>
            </div>
            <div className="group-mark">
              <span className="group-avatar">G5</span>
              <div>
                <strong>{GROUP_NAME}</strong>
                <small>Introduction to Data Science</small>
              </div>
            </div>
          </div>
        </aside>
        <div className="workspace">
          <header className="topbar">
            <div className="breadcrumb">
              <Button
                id="menu-toggle"
                className="mobile-menu"
                variant="ghost"
                size="icon"
                aria-label={open ? 'Close navigation' : 'Open navigation'}
                aria-expanded={open}
                aria-controls="site-navigation"
                onClick={() => setOpen(!open)}
              >
                {open ? <X size={20} /> : <Menu size={20} />}
              </Button>
              <span>Research workspace</span>
              <ChevronRight size={14} />
              <strong>{current?.label || 'Not found'}</strong>
            </div>
            <div className="topbar-right">
              <span className="release-status">
                <i className="dot cyan" />
                {data
                  ? data.mode === 'supabase'
                    ? 'Supabase release'
                    : 'Published snapshot'
                  : 'Loading release'}
              </span>
              {data && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    download(
                      JSON.stringify(data.research, null, 2),
                      'undersea-research-snapshot.json',
                    )
                  }
                >
                  <Download size={14} />
                  <span className="export-label">Export snapshot</span>
                </Button>
              )}
            </div>
          </header>
          <main id="main-content" tabIndex={-1} className="container-fluid content">
            {error ? (
              <div className="error-page" role="alert">
                <Database size={36} />
                <h1>Research data unavailable</h1>
                <p>{error}</p>
                <p>
                  Check your data-source configuration. No fake or replacement records were loaded.
                </p>
                <Button onClick={() => setAttempt((v) => v + 1)}>Retry loading</Button>
              </div>
            ) : !data ? (
              <div className="loading-page" role="status">
                <LoaderCircle size={32} className="spin" />
                <h1>Opening the research workspace</h1>
                <p>Loading and validating the published records…</p>
              </div>
            ) : (
              <Routes>
                <Route path="/" element={<Overview {...data} />} />
                <Route path="/dataset" element={<Dataset {...data} />} />
                <Route path="/models" element={<Models {...data} />} />
                <Route path="/predict" element={<Demonstrator {...data} />} />
                <Route path="/interpretation" element={<Interpretation {...data} />} />
                <Route path="/methodology" element={<Methodology {...data} />} />
                <Route path="/summary" element={<Summary {...data} />} />
                <Route path="/about" element={<About {...data} />} />
                <Route
                  path="*"
                  element={
                    <div className="error-page">
                      <h1>Page not found</h1>
                      <Button asChild>
                        <Link to="/">Return to overview</Link>
                      </Button>
                    </div>
                  }
                />
              </Routes>
            )}
          </main>
          <footer className="footer">
            <span>Undersea Research · {GROUP_NAME}</span>
            <span>
              Research evidence, with its limitations.
              <Link to="/about">
                Sources & provenance
                <ArrowUpRight size={13} />
              </Link>
            </span>
          </footer>
        </div>
      </div>
    </ErrorBoundary>
  );
}
