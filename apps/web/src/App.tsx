import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom';
import { LiveSandboxPage } from './pages/LiveSandboxPage';
import { HomePage } from './pages/HomePage';
import { StateboardPage } from './pages/StateboardPage';

function Shell() {
  const { pathname } = useLocation();
  const fullscreen = pathname === '/live' || pathname === '/stateboard' || pathname === '/';

  return (
    <div style={{ height: fullscreen ? '100%' : undefined }}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/live" element={<LiveSandboxPage />} />
        <Route path="/stateboard" element={<StateboardPage />} />
        <Route
          path="*"
          element={
            <div className="home">
              <p>Not found</p>
              <Link to="/">Home</Link>
            </div>
          }
        />
      </Routes>
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  );
}
