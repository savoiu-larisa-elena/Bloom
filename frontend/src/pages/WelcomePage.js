import { Link, Navigate } from 'react-router-dom';
import { getToken } from '../authStorage';
import { EtherealScene, FairyDivider, GlassCard } from '../components/EtherealScene';
import { Shell, WelcomeTopBar } from '../components/Layout';

export default function WelcomePage() {
  if (getToken()) {
    return <Navigate to="/home" replace />;
  }

  return (
    <Shell>
      <WelcomeTopBar />
      <main className="welcome-main">
        <EtherealScene className="welcome-scene" variant="minimal">
          <GlassCard className="welcome-card">
            <h1 className="welcome-title">
              Welcome to Bloom.
              <span className="welcome-title-accent"> Make your story grow!</span>
            </h1>
            <FairyDivider />
            <p className="welcome-sub">
              Soft light, quiet moss, ink on petals, feel free to pick your path through the garden
              gate.
            </p>
            <div className="welcome-buttons">
              <Link className="welcome-btn welcome-btn--primary" to="/login">
                <span className="welcome-btn-spark" aria-hidden>
                  ✧
                </span>
                Take me back
              </Link>
              <Link className="welcome-btn welcome-btn--ghost" to="/register">
                <span className="welcome-btn-spark" aria-hidden>
                  ✧
                </span>
                I'm new here
              </Link>
            </div>
          </GlassCard>
        </EtherealScene>
      </main>
    </Shell>
  );
}
