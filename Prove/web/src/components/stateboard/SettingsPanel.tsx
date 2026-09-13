import { X } from 'lucide-react';

type Props = {
  gitUrl: string;
  gitRef: string;
  terraformRoot: string;
  busy: boolean;
  error: string | null;
  onGitUrl: (v: string) => void;
  onGitRef: (v: string) => void;
  onTerraformRoot: (v: string) => void;
  onScanRepo: () => void;
  onSample: () => void;
  onClose: () => void;
};

export function SettingsPanel({
  gitUrl,
  gitRef,
  terraformRoot,
  busy,
  error,
  onGitUrl,
  onGitRef,
  onTerraformRoot,
  onScanRepo,
  onSample,
  onClose,
}: Props) {
  return (
    <aside className="sb-settings-panel" role="dialog" aria-label="Settings">
      <div className="sb-settings-panel-head">
        <h2>Settings</h2>
        <button
          type="button"
          className="sb-icon-btn"
          aria-label="Close settings"
          onClick={onClose}
        >
          <X size={16} />
        </button>
      </div>
      <div className="sb-settings-panel-body">
        <p className="sb-settings-lead">
          Clone an external git repo, scan HCL, estimate cost, and redraw the map.
        </p>
        <label htmlFor="sb-git-url">Git repository URL</label>
        <input
          id="sb-git-url"
          value={gitUrl}
          onChange={(e) => onGitUrl(e.target.value)}
          placeholder="https://github.com/org/infra"
        />
        <label htmlFor="sb-git-ref">Branch / tag (optional)</label>
        <input
          id="sb-git-ref"
          value={gitRef}
          onChange={(e) => onGitRef(e.target.value)}
          placeholder="leave empty for default"
        />
        <label htmlFor="sb-tf-root">Terraform root</label>
        <input
          id="sb-tf-root"
          value={terraformRoot}
          onChange={(e) => onTerraformRoot(e.target.value)}
          placeholder="auto-detect"
        />
        <div className="sb-scan-actions">
          <button
            type="button"
            className="home-btn"
            style={{ width: '100%', justifyContent: 'center' }}
            disabled={busy}
            onClick={onScanRepo}
          >
            {busy ? 'Scanning…' : 'Scan repository'}
          </button>
          <button
            type="button"
            className="home-btn home-btn--ghost"
            style={{ width: '100%', justifyContent: 'center' }}
            disabled={busy}
            onClick={onSample}
          >
            Sample fixture
          </button>
        </div>
        {error && <p className="sb-scan-error">{error}</p>}
      </div>
    </aside>
  );
}
