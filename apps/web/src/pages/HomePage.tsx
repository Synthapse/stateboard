import { Link } from 'react-router-dom';

export function HomePage() {
  return (
    <div className="home">
      <h1>Stateboard</h1>
      <p>
        Terraform state visualizer with RTS-style hex graphics. Scan state, draw the estate,
        calculate cloud costs via <code>@stateboard/tf-cost</code>.
      </p>
      <div className="home-actions">
        <Link className="home-btn" to="/live">
          RTS graphics lab
        </Link>
        <Link className="home-btn home-btn--ghost" to="/stateboard">
          Stateboard (WIP)
        </Link>
      </div>
    </div>
  );
}
