import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { API_BASE } from '../api';
import { authHeaders, getToken } from '../authStorage';
import { FairyDivider, GlassCard } from '../components/EtherealScene';
import { AppNav, Shell } from '../components/Layout';

function retentionLabel(days) {
  if (days === 7) return 'seven days';
  if (days === 30) return 'thirty days';
  return `${days} days`;
}

export default function HomePage() {
  const navigate = useNavigate();
  const [entries, setEntries] = useState([]);
  const [count, setCount] = useState(0);
  const [retentionDays, setRetentionDays] = useState(7);
  const [msg, setMsg] = useState('');
  const [deletingId, setDeletingId] = useState(null);
  const [characterThreads, setCharacterThreads] = useState([]);

  const loadDashboard = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/history/dashboard`, {
        headers: { ...authHeaders() },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setMsg(typeof data.detail === 'string' ? data.detail : 'Could not load your dashboard.');
        return;
      }
      setRetentionDays(typeof data.retention_days === 'number' ? data.retention_days : 7);
      setCount(typeof data.analysis_count === 'number' ? data.analysis_count : 0);
      setEntries(Array.isArray(data.entries) ? data.entries : []);
      if (typeof data.history_warning === 'string' && data.history_warning.trim()) {
        setMsg(data.history_warning);
      } else {
        setMsg('');
      }
    } catch {
      setMsg(`Could not reach the API. Is the backend running on ${API_BASE}?`);
    }
  }, []);

  const loadCharacterThreads = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/history/characters/evolution`, {
        headers: { ...authHeaders() },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) return;
      setCharacterThreads(Array.isArray(data.characters) ? data.characters : []);
    } catch {
    }
  }, []);

  useEffect(() => {
    if (!getToken()) return;
    void (async () => {
      await loadDashboard();
      await loadCharacterThreads();
    })();
  }, [loadDashboard, loadCharacterThreads]);

  async function handleDelete(id) {
    if (!window.confirm('Remove this draft from your history?')) return;
    setDeletingId(id);
    try {
      const res = await fetch(`${API_BASE}/api/history/${id}`, {
        method: 'DELETE',
        headers: { ...authHeaders() },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setMsg(typeof data.detail === 'string' ? data.detail : 'Could not delete that entry.');
        return;
      }
      await loadDashboard();
      await loadCharacterThreads();
    } catch {
      setMsg('Could not reach the API to delete that entry.');
    } finally {
      setDeletingId(null);
    }
  }

  const stats = useMemo(() => {
    const list = entries.filter((e) => e.summary);
    if (!list.length) {
      return { avgFlesch: null, topEmotion: null, grammarTotal: null };
    }
    const fre = list
      .map((e) => e.summary?.flesch_score)
      .filter((n) => typeof n === 'number' && !Number.isNaN(n));
    const avgFlesch =
      fre.length > 0 ? Math.round((fre.reduce((a, b) => a + b, 0) / fre.length) * 10) / 10 : null;
    const emotionCounts = {};
    for (const e of list) {
      const em = e.summary?.dominant_emotion;
      if (typeof em === 'string' && em.trim()) {
        emotionCounts[em] = (emotionCounts[em] || 0) + 1;
      }
    }
    const topEmotion =
      Object.keys(emotionCounts).length > 0
        ? Object.entries(emotionCounts).sort((a, b) => b[1] - a[1])[0][0]
        : null;
    const grammarVals = list
      .map((e) => e.summary?.grammar_issue_count)
      .filter((n) => typeof n === 'number' && !Number.isNaN(n));
    const grammarTotal =
      grammarVals.length > 0 ? grammarVals.reduce((a, b) => a + b, 0) : null;
    return { avgFlesch, topEmotion, grammarTotal };
  }, [entries]);

  const period = retentionLabel(retentionDays);

  if (!getToken()) {
    return <Navigate to="/login" replace />;
  }

  return (
    <Shell>
      <AppNav subtitle={`Your last ${period}...`} />
      <main className="app-main home-main fairy-garden">
        <GlassCard className="home-hero" fairy>
          <h1 className="home-heading">Petals &amp; pages await</h1>
          <FairyDivider />
          <p className="home-lead">
            Here&apos;s what you&apos;ve shared in the last {period} — snippets, moods, and little
            numbers that remember with you.
          </p>
          <button
            type="button"
            className="button button-dream button-fairy"
            onClick={() => navigate('/analyse')}
          >
            <span className="button-fairy-spark" aria-hidden>
              ✦
            </span>
            Got another draft ready?
          </button>
        </GlassCard>

        {msg ? <p className="status">{msg}</p> : null}

        <section className="home-stats" aria-label="History overview">
          <div className="stat-card stat-card--fairy">
            <span className="stat-card-spark" aria-hidden>
              ✧
            </span>
            <p className="stat-label">Drafts saved</p>
            <p className="stat-value">{count}</p>
          </div>
          <div className="stat-card stat-card--fairy">
            <span className="stat-card-spark" aria-hidden>
              ✧
            </span>
            <p className="stat-label">Avg. reading ease</p>
            <p className="stat-value">{stats.avgFlesch != null ? stats.avgFlesch : '—'}</p>
          </div>
          <div className="stat-card stat-card--fairy">
            <span className="stat-card-spark" aria-hidden>
              ✧
            </span>
            <p className="stat-label">Mood you visit most</p>
            <p className="stat-value stat-value--small">
              {stats.topEmotion ? stats.topEmotion : '—'}
            </p>
          </div>
          <div className="stat-card stat-card--fairy">
            <span className="stat-card-spark" aria-hidden>
              ✧
            </span>
            <p className="stat-label">Grammar notes (sum)</p>
            <p className="stat-value">{stats.grammarTotal != null ? stats.grammarTotal : '—'}</p>
          </div>
        </section>

        <section className="home-history" aria-label="Recent uploads">
          <h2 className="home-section-title">
            <span className="home-section-gem" aria-hidden>
              ✦
            </span>
            What you uploaded
          </h2>
          {entries.length === 0 ? (
            <p className="hint home-empty">
              No drafts saved yet. When you analyse text, it will appear here like pressed flowers in
              a journal.
            </p>
          ) : (
            <ul className="history-list">
              {entries.map((e) => (
                <li key={e.id} className="history-row">
                  <button
                    type="button"
                    className="history-item"
                    onClick={() =>
                      navigate('/analyse', {
                        state: { prefill: e.full_text || e.text_preview || '' },
                      })
                    }
                  >
                    <span className="history-meta">
                      {e.created_at?.replace('T', ' ').slice(0, 19)}
                    </span>
                    <span className="history-preview">{e.text_preview}</span>
                    {e.summary && (
                      <span className="history-stats">
                        {e.summary.flesch_score != null && (
                          <span>FRE {e.summary.flesch_score}</span>
                        )}
                        {e.summary.dominant_emotion && (
                          <span> · {e.summary.dominant_emotion}</span>
                        )}
                        {e.summary.grammar_issue_count != null && (
                          <span> · grammar {e.summary.grammar_issue_count}</span>
                        )}
                      </span>
                    )}
                    {e.characters?.profiles?.length > 0 && (
                      <span className="history-characters">
                        {e.characters.profiles.slice(0, 3).map((p) => (
                          <span key={p.name} className="history-character-chip">
                            {p.name}
                            {p.traits?.length ? ` · ${p.traits.slice(0, 2).join(', ')}` : ''}
                          </span>
                        ))}
                      </span>
                    )}
                  </button>
                  <button
                    type="button"
                    className="history-delete"
                    aria-label="Delete this draft from history"
                    disabled={deletingId === e.id}
                    onClick={() => handleDelete(e.id)}
                  >
                    {deletingId === e.id ? '…' : '×'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="home-characters" aria-label="Character evolution">
          <h2 className="home-section-title">
            <span className="home-section-gem" aria-hidden>
              ✦
            </span>
            Character threads
          </h2>
          {characterThreads.length === 0 ? (
            <p className="hint home-empty">
              When deep character profiling runs on your drafts, Bloom saves each character&apos;s
              goals, traits, and arc beats here so you can see how they shift over time.
            </p>
          ) : (
            <ul className="character-thread-list">
              {characterThreads.map((thread) => (
                <li key={thread.name} className="character-thread-card">
                  <h3 className="character-thread-name">{thread.name}</h3>
                  <p className="hint character-thread-count">
                    {thread.snapshots.length} saved snapshot
                    {thread.snapshots.length === 1 ? '' : 's'} in the last {retentionDays} days
                  </p>
                  <ol className="character-snapshot-list">
                    {thread.snapshots.map((snap) => (
                      <li key={`${thread.name}-${snap.analysis_id}-${snap.created_at}`}>
                        <span className="character-snapshot-date">
                          {snap.created_at?.replace('T', ' ').slice(0, 19)}
                        </span>
                        {snap.role_hint && snap.role_hint !== 'unknown' && (
                          <span className="character-snapshot-role"> · {snap.role_hint}</span>
                        )}
                        {snap.goals_or_motivation && (
                          <p className="character-snapshot-line">{snap.goals_or_motivation}</p>
                        )}
                        {snap.traits?.length > 0 && (
                          <p className="character-snapshot-traits">
                            Traits: {snap.traits.join(', ')}
                          </p>
                        )}
                        {snap.arc_beat && (
                          <p className="character-snapshot-arc">In this passage: {snap.arc_beat}</p>
                        )}
                        {snap.text_preview && (
                          <p className="character-snapshot-preview">&ldquo;{snap.text_preview}&rdquo;</p>
                        )}
                      </li>
                    ))}
                  </ol>
                </li>
              ))}
            </ul>
          )}
        </section>

        <p className="hint home-foot">
          Saved drafts are kept for {retentionDays} days. Want to tweak your account?{' '}
          <Link to="/profile" className="inline-link">
            Visit My profile
          </Link>
          .
        </p>
      </main>
    </Shell>
  );
}
