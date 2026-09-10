import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { API_BASE } from '../api';
import { getToken, setToken } from '../authStorage';
import { EtherealScene, FairyDivider, GlassCard } from '../components/EtherealScene';
import { Shell, WelcomeTopBar } from '../components/Layout';

export default function RegisterPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  if (getToken()) {
    return <Navigate to="/home" replace />;
  }

  async function onSubmit(e) {
    e.preventDefault();
    setError('');
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(typeof data.detail === 'string' ? data.detail : 'Registration failed');
      return;
    }
    setToken(data.access_token);
    navigate('/home', { replace: true });
  }

  return (
    <Shell>
      <div className="auth-page">
        <WelcomeTopBar />
        <main className="app-main auth-main auth-main--centered">
          <EtherealScene className="auth-scene">
            <GlassCard className="auth-glass-card">
              <h1 className="auth-title">Register</h1>
              <p className="auth-tagline">Begin your garden...</p>
              <FairyDivider />
              <p className="hint auth-sub">
                Username: 3–32 characters (letters, digits, underscore). Password: at least 8
                characters.
              </p>
              <form className="auth-form auth-form--centered" onSubmit={onSubmit}>
                <label className="label" htmlFor="reg-user">
                  Username
                </label>
                <input
                  id="reg-user"
                  className="auth-input"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
                <label className="label" htmlFor="reg-pass">
                  Password
                </label>
                <input
                  id="reg-pass"
                  type="password"
                  className="auth-input"
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                {error ? <p className="grammar-unavailable">{error}</p> : null}
                <button type="submit" className="button auth-submit">
                  Create account
                </button>
              </form>
              <p className="hint home-foot">
                Already have an account?{' '}
                <Link to="/login" className="inline-link">
                  Log in
                </Link>
              </p>
            </GlassCard>
          </EtherealScene>
        </main>
      </div>
    </Shell>
  );
}
