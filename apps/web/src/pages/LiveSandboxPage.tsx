import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { LiveSandboxView } from '../components/live/LiveSandboxView';

export function LiveSandboxPage() {
  return (
    <div className="live-page">
      <div className="live-page-bar">
        <Link to="/" className="live-page-back" aria-label="Back home">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <p className="live-page-title">Ascension Live</p>
          <p className="live-page-sub">RTS graphics lab — hex board + sprites</p>
        </div>
        <span className="live-page-badge">Lab</span>
      </div>
      <LiveSandboxView />
    </div>
  );
}
