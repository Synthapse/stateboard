import { Link } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import './landing.css';

const REPO = 'https://github.com/Synthapse/stateboard';
const CLONE = 'git clone https://github.com/Synthapse/stateboard.git';

export function HomePage() {
  const heroRef = useRef<HTMLElement>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const root = heroRef.current;
    if (!root) return;
    requestAnimationFrame(() => root.classList.add('is-ready'));
  }, []);

  const copyClone = async () => {
    try {
      await navigator.clipboard.writeText(CLONE);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="lp">
      <header className="lp-nav">
        <a className="lp-nav-brand" href="#top">
          Stateboard
        </a>
        <nav className="lp-nav-links" aria-label="Primary">
          <a href="#what">Product</a>
          <a href="#preview">Preview</a>
          <a href="#how">How it works</a>
          <a href="#contribute">Contribute</a>
          <a href={REPO} target="_blank" rel="noreferrer">
            GitHub
          </a>
          <Link className="lp-nav-cta" to="/stateboard">
            Open map
          </Link>
        </nav>
      </header>

      <main id="top">
        <section className="lp-hero" ref={heroRef} aria-label="Hero">
          <div className="lp-hero-copy">
            <h1 className="lp-headline">Terraform architecture, mapped and costed.</h1>
            <p className="lp-lede">
              Point Stateboard at a Git repository. It scans your HCL, groups resources by role,
              estimates monthly cloud spend, and renders a clear spatial view of the estate —
              ready for reviews, onboarding, and cost conversations.
            </p>
            <div className="lp-cta">
              <Link className="lp-btn lp-btn--primary" to="/stateboard">
                Open the map
              </Link>
              <a className="lp-btn lp-btn--ghost" href={REPO} target="_blank" rel="noreferrer">
                View on GitHub
              </a>
            </div>
          </div>
          <div className="lp-hero-visual" aria-hidden="true">
            <div className="lp-hero-glow" />
            <img
              className="lp-hero-img"
              src="/hero-map.png"
              alt=""
              width={1600}
              height={900}
              decoding="async"
            />
            <div className="lp-hex-field" />
          </div>
        </section>

        <section className="lp-section" id="what">
          <p className="lp-kicker">Product</p>
          <h2 className="lp-section-title">Infrastructure clarity for teams that ship Terraform.</h2>
          <p className="lp-section-lede">
            Spreadsheets and raw graphs obscure how an estate actually fits together. Stateboard
            turns the Terraform you already keep in Git into a structured map: what exists, how it
            connects, and what it roughly costs — without installing an agent in your cloud account.
          </p>

          <div className="lp-explain">
            <div className="lp-explain-block">
              <h3>The problem</h3>
              <p>
                Large Terraform monorepos scatter resources across modules. PR review and onboarding
                become file-by-file archaeology, with little sense of system shape or spend.
              </p>
            </div>
            <div className="lp-explain-block">
              <h3>What you get</h3>
              <p>
                An architecture board color-coded by destination (compute, database, storage,
                network, identity), dependency links, and a detail panel with types, SKUs, modules,
                and estimated monthly cost.
              </p>
            </div>
            <div className="lp-explain-block">
              <h3>Who it’s for</h3>
              <p>
                Platform, SRE, and FinOps teams that need a shared picture of infra — and engineers
                who prefer an open codebase over a closed SaaS black box.
              </p>
            </div>
          </div>

          <dl className="lp-facts">
            <div>
              <dt>Input</dt>
              <dd>Git URL of a Terraform repo (or the built-in sample)</dd>
            </div>
            <div>
              <dt>Engine</dt>
              <dd>.NET API clones, parses HCL, runs the cost module</dd>
            </div>
            <div>
              <dt>Output</dt>
              <dd>React + Three.js map with structure inspector</dd>
            </div>
            <div>
              <dt>License</dt>
              <dd>Open source (Synthapse) — contributions welcome</dd>
            </div>
          </dl>
        </section>

        <section className="lp-section" id="preview">
          <p className="lp-kicker">In the product</p>
          <h2 className="lp-section-title">See the estate the way your team talks about it.</h2>
          <p className="lp-section-lede">
            Structure on the left, the hex map in the middle, and a selected resource on the right —
            with plain-language explainers, SKUs, dependencies, and estimated $/mo. GenAI insight
            suggests improvements and how to split the stack into Terraform modules.
          </p>

          <figure className="lp-product-shot">
            <img
              src="/product-map.jpg"
              alt="Stateboard map with Structure panel, hex architecture board, and selected resource details"
              width={2880}
              height={1800}
              loading="lazy"
              decoding="async"
            />
            <figcaption>
              Live board: destination groups, dependency links, and cost on every resource — from a
              Git Terraform scan, no cloud agent required.
            </figcaption>
          </figure>
        </section>

        <section className="lp-section" id="how">
          <p className="lp-kicker">How it works</p>
          <h2 className="lp-section-title">From repository to architecture view in three steps.</h2>
          <p className="lp-section-lede">
            No cloud-account agent for the MVP. Stateboard reads Terraform source from Git and
            renders locally in the browser.
          </p>
          <ol className="lp-steps">
            <li>
              <span className="lp-step-num">01</span>
              <div>
                <h3>Scan the repository</h3>
                <p>
                  The API shallow-clones your repo (falls back to the default branch if{' '}
                  <code>main</code> is missing), locates the Terraform root, and extracts resources,
                  modules, and references from <code>*.tf</code> files.
                </p>
              </div>
            </li>
            <li>
              <span className="lp-step-num">02</span>
              <div>
                <h3>Estimate cost</h3>
                <p>
                  Each resource is classified (compute, database, disk, network…) and priced from
                  local AWS / Azure / GCP pricebooks so relative monthly spend is visible on the map.
                </p>
              </div>
            </li>
            <li>
              <span className="lp-step-num">03</span>
              <div>
                <h3>Review the estate</h3>
                <p>
                  Resources are laid out by destination group. Select a unit for SKU, region,
                  dependencies, and cost — or browse the Structure panel as a tree of the
                  architecture.
                </p>
              </div>
            </li>
          </ol>
          <p className="lp-after-steps">
            Ready to try it?{' '}
            <Link to="/stateboard">Open the architecture map</Link>
            {' · '}
            <Link to="/live">Graphics sandbox</Link>
          </p>
        </section>

        <section className="lp-section lp-section--contribute" id="contribute">
          <p className="lp-kicker">Contribute</p>
          <h2 className="lp-section-title">Open source. Built for extension.</h2>
          <p className="lp-section-lede">
            Stateboard is a public project for engineers improving infra tooling: HCL parsing, cost
            models, map UX, and documentation. Fork the repo, open a PR, or file an issue.
          </p>

          <div className="lp-contribute-row">
            <div className="lp-clone">
              <p className="lp-clone-label">Clone the project</p>
              <code className="lp-clone-cmd">{CLONE}</code>
              <button type="button" className="lp-copy" onClick={() => void copyClone()}>
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <div className="lp-contribute-actions">
              <a className="lp-btn lp-btn--primary" href={REPO} target="_blank" rel="noreferrer">
                Open repository
              </a>
              <a
                className="lp-btn lp-btn--ghost"
                href={`${REPO}/issues/new`}
                target="_blank"
                rel="noreferrer"
              >
                File an issue
              </a>
              <a
                className="lp-btn lp-btn--ghost"
                href={`${REPO}/blob/main/README.md`}
                target="_blank"
                rel="noreferrer"
              >
                Read the README
              </a>
            </div>
          </div>

          <ul className="lp-stack">
            <li>
              <strong>Stack</strong> .NET 8 API · React · Three.js · Vite monorepo
            </li>
            <li>
              <strong>Good first PRs</strong> richer Azure/GCP prices · HCL coverage · map legends ·
              docs
            </li>
            <li>
              <strong>Repository</strong>{' '}
              <a href={REPO} target="_blank" rel="noreferrer">
                Synthapse/stateboard
              </a>
            </li>
          </ul>
        </section>
      </main>

      <footer className="lp-footer">
        <span>Stateboard — Terraform architecture, visualized</span>
        <a href={REPO} target="_blank" rel="noreferrer">
          Contribute on GitHub
        </a>
        <Link to="/stateboard">Open map</Link>
      </footer>
    </div>
  );
}
