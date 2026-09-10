import { useEffect, useState } from 'react';
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from 'react-router-dom';
import './App.css';
import { API_BASE } from './api';
import { authHeaders, clearToken, getToken } from './authStorage';
import { AnalyseResults } from './components/AnalyseResults';
import { AppNav, Shell } from './components/Layout';
import { ThemeProvider } from './ThemeContext';
import WelcomePage from './pages/WelcomePage';
import HomePage from './pages/HomePage';
import ProfilePage from './pages/ProfilePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';

function AnalysePage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [text, setText] = useState('');
  const [fleschScore, setFleschScore] = useState(null);
  const [fleschKincaidGrade, setFleschKincaidGrade] = useState(null);
  const [grammar, setGrammar] = useState(null);
  const [neuralGrammar, setNeuralGrammar] = useState(null);
  const [sentimentPolarity, setSentimentPolarity] = useState(null);
  const [emotionTone, setEmotionTone] = useState(null);
  const [paraphrase, setParaphrase] = useState(null);
  const [linguistics, setLinguistics] = useState(null);
  const [spacyNlp, setSpacyNlp] = useState(null);
  const [styleConsistency, setStyleConsistency] = useState(null);
  const [characters, setCharacters] = useState(null);
  const [dialogue, setDialogue] = useState(null);
  const [coreference, setCoreference] = useState(null);
  const [characterProfile, setCharacterProfile] = useState(null);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const pre = location.state && location.state.prefill;
    if (typeof pre === 'string' && pre.trim()) {
      setText(pre);
      setMessage('Loaded text from your dashboard. You can edit before analysing.');
      navigate('/analyse', { replace: true, state: {} });
    }
  }, [location.state, navigate]);

  async function handleAnalyse() {
    setMessage('');
    setFleschScore(null);
    setFleschKincaidGrade(null);
    setGrammar(null);
    setNeuralGrammar(null);
    setSentimentPolarity(null);
    setEmotionTone(null);
    setParaphrase(null);
    setLinguistics(null);
    setSpacyNlp(null);
    setStyleConsistency(null);
    setCharacters(null);
    setDialogue(null);
    setCoreference(null);
    setCharacterProfile(null);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/analyse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ text }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        setMessage(data.detail || `Request failed (${res.status})`);
        return;
      }

      if (data.error) {
        setMessage(data.error);
        return;
      }

      if (data.flesch_score != null) {
        setFleschScore(data.flesch_score);
        setFleschKincaidGrade(data.flesch_kincaid_grade ?? null);
        setGrammar(data.grammar ?? null);
        setNeuralGrammar(data.neural_grammar ?? null);
        setSentimentPolarity(data.sentiment_polarity ?? null);
        setEmotionTone(data.emotion_tone ?? null);
        setParaphrase(data.paraphrase ?? null);
        setLinguistics(data.linguistics ?? null);
        setSpacyNlp(data.spacy_nlp ?? null);
        setStyleConsistency(data.style_consistency ?? null);
        setCharacters(data.characters ?? null);
        setDialogue(data.dialogue ?? null);
        setCoreference(data.coreference ?? null);
        setCharacterProfile(data.character_profile ?? null);
        setMessage(
          data.history_warning
            ? `Analysis complete. ${data.history_warning}`
            : 'Analysis complete. Saved to your history.'
        );
      } else {
        setMessage('No score returned.');
      }
    } catch (err) {
      setMessage(
        'Could not reach the API. Is the backend running on ' + API_BASE + '?'
      );
    } finally {
      setLoading(false);
    }
  }

  if (!getToken()) {
    return <Navigate to="/login" replace />;
  }

  const hasAnalysisResults =
    fleschScore != null ||
    fleschKincaidGrade != null ||
    grammar ||
    neuralGrammar ||
    sentimentPolarity ||
    emotionTone ||
    paraphrase ||
    linguistics ||
    spacyNlp ||
    styleConsistency ||
    characters ||
    dialogue ||
    coreference ||
    characterProfile;

  return (
    <Shell>
      <AppNav subtitle="Analyse your draft" />

      <main className="app-main analyse-main">
        <label htmlFor="story-text" className="label">
          Your text
        </label>
        <textarea
          id="story-text"
          className="textarea"
          rows={12}
          placeholder="Paste a paragraph from your story…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={loading}
        />

        <div className="actions">
          <button
            type="button"
            className="button"
            onClick={handleAnalyse}
            disabled={loading}
          >
            {loading ? 'Analysing…' : 'Analyse'}
          </button>
        </div>

        {message && !hasAnalysisResults && <p className="status">{message}</p>}

        {hasAnalysisResults && (
          <AnalyseResults
            message={message}
            fleschScore={fleschScore}
            fleschKincaidGrade={fleschKincaidGrade}
            grammar={grammar}
            neuralGrammar={neuralGrammar}
            sentimentPolarity={sentimentPolarity}
            emotionTone={emotionTone}
            paraphrase={paraphrase}
            linguistics={linguistics}
            spacyNlp={spacyNlp}
            styleConsistency={styleConsistency}
            characters={characters}
            dialogue={dialogue}
            coreference={coreference}
            characterProfile={characterProfile}
          />
        )}
      </main>
    </Shell>
  );
}

function AppRoutes() {
  const [authReady, setAuthReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function validateSession() {
      const token = getToken();
      if (!token) {
        if (!cancelled) setAuthReady(true);
        return;
      }

      try {
        const res = await fetch(`${API_BASE}/api/auth/me`, { headers: { ...authHeaders() } });
        if (!res.ok) {
          clearToken();
        }
      } catch {
      }

      if (!cancelled) setAuthReady(true);
    }

    validateSession();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!authReady) {
    return (
      <Shell>
        <main className="app-main auth-main auth-main--centered">
          <p className="hint">Opening the garden…</p>
        </main>
      </Shell>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<WelcomePage />} />
      <Route path="/welcome" element={<Navigate to="/" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/home" element={<HomePage />} />
      <Route path="/profile" element={<ProfilePage />} />
      <Route path="/analyse" element={<AnalysePage />} />
      <Route path="/analyze" element={<Navigate to="/analyse" replace />} />
      <Route path="/my-history" element={<Navigate to="/home" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AppRoutes />
      </ThemeProvider>
    </BrowserRouter>
  );
}
