import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { API_BASE } from '../api';
import { authHeaders, getToken, setToken } from '../authStorage';
import { AppNav, Shell } from '../components/Layout';

const MASK = '••••••••';

export default function ProfilePage() {
  const [username, setUsername] = useState('');
  const [analysisCount, setAnalysisCount] = useState(0);
  const [retentionDays, setRetentionDays] = useState(7);
  const [loadErr, setLoadErr] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [formMsg, setFormMsg] = useState('');
  const [saving, setSaving] = useState(false);
  const [currentPwReadOnly, setCurrentPwReadOnly] = useState(true);
  const [newUserReadOnly, setNewUserReadOnly] = useState(true);

  useEffect(() => {
    if (!getToken()) return;
    (async () => {
      setLoadErr('');
      try {
        const [meRes, dashRes] = await Promise.all([
          fetch(`${API_BASE}/api/auth/me`, { headers: { ...authHeaders() } }),
          fetch(`${API_BASE}/api/history/dashboard?limit=1`, { headers: { ...authHeaders() } }),
        ]);
        const me = await meRes.json().catch(() => ({}));
        const dash = await dashRes.json().catch(() => ({}));
        if (!meRes.ok) {
          setLoadErr(typeof me.detail === 'string' ? me.detail : 'Could not load profile.');
          return;
        }
        setUsername(me.username || '');
        if (dashRes.ok) {
          if (typeof dash.analysis_count === 'number') {
            setAnalysisCount(dash.analysis_count);
          }
          if (typeof dash.retention_days === 'number') {
            setRetentionDays(dash.retention_days);
          }
        } else if (typeof dash.history_warning === 'string' && dash.history_warning.trim()) {
          setLoadErr(dash.history_warning);
        }
      } catch {
        setLoadErr(`Could not reach the API. Is the backend running on ${API_BASE}?`);
      }
    })();
  }, []);

  if (!getToken()) {
    return <Navigate to="/login" replace />;
  }

  async function onSave(e) {
    e.preventDefault();
    setFormMsg('');
    const nu = newUsername.trim();
    const np = newPassword;
    if (!nu && !np) {
      setFormMsg('Enter a new username and/or a new password to save changes.');
      return;
    }
    setSaving(true);
    try {
      const payload = { current_password: currentPassword };
      if (nu) payload.new_username = nu;
      if (np) payload.new_password = np;
      const res = await fetch(`${API_BASE}/api/auth/me`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setFormMsg(typeof data.detail === 'string' ? data.detail : 'Could not update profile.');
        return;
      }
      if (data.access_token) setToken(data.access_token);
      if (data.username) setUsername(data.username);
      setCurrentPassword('');
      setNewUsername('');
      setNewPassword('');
      setCurrentPwReadOnly(true);
      setNewUserReadOnly(true);
      setFormMsg('Saved. Your session token was refreshed.');
    } catch {
      setFormMsg('Could not reach the API.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Shell>
      <AppNav subtitle="Your account" />
      <main className="app-main profile-main">
        {loadErr ? <p className="grammar-unavailable">{loadErr}</p> : null}

        <section className="profile-card-dream" aria-labelledby="profile-heading">
          <h1 id="profile-heading" className="profile-title">
            My profile
          </h1>
          <dl className="profile-dl">
            <div>
              <dt>Username</dt>
              <dd>{username || '—'}</dd>
            </div>
            <div>
              <dt>Password</dt>
              <dd className="profile-mask">{MASK}</dd>
            </div>
          </dl>
          <p className="hint profile-secret-note">
            Your real password is never shown or stored in plain text — only this soft mask.
          </p>
        </section>

        <section className="profile-card-dream" aria-labelledby="count-heading">
          <h2 id="count-heading" className="profile-section-title">
            Drafts in the last {retentionDays} days
          </h2>
          <p className="profile-big-count">{analysisCount}</p>
          <p className="hint">
            Each analysis you run while signed in counts toward this total. Older entries are removed
            automatically after {retentionDays} days.
          </p>
        </section>

        <section className="profile-card-dream" aria-labelledby="change-heading">
          <h2 id="change-heading" className="profile-section-title">
            Change username or password
          </h2>
          <p className="hint">Confirm with your current password.</p>
          <form className="auth-form profile-form" onSubmit={onSave} autoComplete="off">
            <label className="label" htmlFor="cur-pw">
              Current password
            </label>
            <input
              id="cur-pw"
              type="password"
              className="auth-input"
              name="bloom-profile-current-password"
              autoComplete="off"
              readOnly={currentPwReadOnly}
              onFocus={() => setCurrentPwReadOnly(false)}
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
            <label className="label" htmlFor="new-user">
              New username (optional)
            </label>
            <input
              id="new-user"
              className="auth-input"
              name="bloom-profile-new-username"
              autoComplete="off"
              readOnly={newUserReadOnly}
              onFocus={() => setNewUserReadOnly(false)}
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
            />
            <label className="label" htmlFor="new-pw">
              New password (optional, min 8 characters)
            </label>
            <input
              id="new-pw"
              type="password"
              className="auth-input"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            {formMsg ? (
              <p className={formMsg.startsWith('Saved') ? 'status' : 'grammar-unavailable'}>{formMsg}</p>
            ) : null}
            <button type="submit" className="button auth-submit" disabled={saving}>
              {saving ? 'Saving…' : 'Save changes'}
            </button>
          </form>
        </section>
      </main>
    </Shell>
  );
}
