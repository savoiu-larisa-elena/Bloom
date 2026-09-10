import { Link, useNavigate } from 'react-router-dom';
import { WhimsicalBackground } from './WhimsicalBackground';
import { clearToken, getToken } from '../authStorage';
import { useTheme } from '../ThemeContext';

export function Shell({ children }) {
  const { theme } = useTheme();
  return (
    <div className={theme === 'light' ? 'app app--light' : 'app'}>
      <WhimsicalBackground />
      <div className="app-surface">{children}</div>
    </div>
  );
}

export function AppNav({ title = 'Bloom', subtitle = 'watch your story grow', showBrandSubtitle = true }) {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const authed = !!getToken();

  return (
    <header className="app-header">
      <div className="app-header-row">
        <div className="brand">
          <Link to={authed ? '/home' : '/'} className="brand-link">
            <h1 className="brand-title">
              <span className="brand-spark" aria-hidden>
                ✦
              </span>
              {title}
            </h1>
          </Link>
          {showBrandSubtitle && subtitle ? (
            <p className="brand-subtitle">{subtitle}</p>
          ) : null}
        </div>
        <div className="app-header-actions app-header-actions--row">
          <nav className="nav-links" aria-label="Main">
            {authed ? (
              <>
                <Link to="/home">Home</Link>
                <Link to="/profile">My profile</Link>
              </>
            ) : null}
          </nav>
          <div className="nav-trailing">
            <button
              type="button"
              className="theme-toggle"
              onClick={toggleTheme}
              aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? 'LIGHT' : 'DARK'}
            </button>
            {authed ? (
              <button
                type="button"
                className="nav-text-btn nav-logout"
                onClick={() => {
                  clearToken();
                  navigate('/', { replace: true });
                }}
              >
                Log out
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}

export function WelcomeTopBar() {
  const { theme, toggleTheme } = useTheme();
  return (
    <header className="welcome-topbar">
      <Link to="/" className="welcome-topbar-brand">
        <span className="welcome-topbar-mark">✦</span>
        <span className="welcome-topbar-word">Bloom</span>
        <span className="welcome-topbar-trail" aria-hidden>
          ✧ ✧
        </span>
      </Link>
      <button
        type="button"
        className="theme-toggle theme-toggle--welcome"
        onClick={toggleTheme}
        aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      >
        {theme === 'dark' ? 'LIGHT' : 'DARK'}
      </button>
    </header>
  );
}
