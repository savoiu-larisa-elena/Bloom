import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { API_BASE } from '../api';
import { getToken, setToken } from '../authStorage';
import { EtherealScene, FairyDivider, GlassCard } from '../components/EtherealScene';
import { Shell, WelcomeTopBar } from '../components/Layout';

export default function LoginPage() {
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
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(typeof data.detail === 'string' ? data.detail : 'Login failed');
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
              <h1 className="auth-title">Log in</h1>
              <p className="auth-tagline">Welcome back to your safe space...</p>
              <FairyDivider />
              <form className="auth-form auth-form--centered" onSubmit={onSubmit}>
                <label className="label" htmlFor="login-user">
                  Username
                </label>
                <input
                  id="login-user"
                  className="auth-input"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
                <label className="label" htmlFor="login-pass">
                  Password
                </label>
                <input
                  id="login-pass"
                  type="password"
                  className="auth-input"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                {error ? <p className="grammar-unavailable">{error}</p> : null}
                <button type="submit" className="button auth-submit">
                  Log in
                </button>
              </form>
              <p className="hint home-foot">
                New here?{' '}
                <Link to="/register" className="inline-link">
                  Register
                </Link>
              </p>
            </GlassCard>
          </EtherealScene>
        </main>
      </div>
    </Shell>
  );
}
