type ResultViewProps = {
  filename: string;
  videoUrl: string;
  captionCount: number;
  cutCount: number;
  brollCoverage: number;
  styleScore: number;
  qcPassed: boolean;
  onReset: () => void;
};


export function ResultView({
  filename,
  videoUrl,
  captionCount,
  cutCount,
  brollCoverage,
  styleScore,
  qcPassed,
  onReset
}: ResultViewProps) {
  return (
    <section className="workspace-grid result-view">
      <div className="preview-stage">
        <div className="phone-frame phone-frame-result">
          <video
            aria-label="Edited video preview"
            src={videoUrl}
            controls
            playsInline
          />
        </div>
      </div>

      <div className="job-panel">
        <p className="file-label">Finished · {filename}</p>
        <h1>Your reel is ready.</h1>
        <p className="job-copy">
          Clean speech, balanced loudness, matched color and burned-in
          captions—exported in a social-ready format.
        </p>

        <dl className="result-stats">
          <div>
            <dt>Format</dt>
            <dd>1080 × 1920</dd>
          </div>
          <div>
            <dt>Captions</dt>
            <dd>{captionCount} caption beats</dd>
          </div>
          <div>
            <dt>Visual coverage</dt>
            <dd>{Math.round(brollCoverage * 100)}% visual coverage</dd>
          </div>
          <div>
            <dt>Style score</dt>
            <dd>{Math.round(styleScore)} / 100</dd>
          </div>
          <div>
            <dt>Source cuts</dt>
            <dd>{cutCount}</dd>
          </div>
          <div>
            <dt>Quality control</dt>
            <dd>{qcPassed ? "QC passed" : "Review recommended"}</dd>
          </div>
        </dl>

        <div className="result-actions">
          <a className="button button-primary" href={videoUrl} download>
            Download MP4
          </a>
          <button
            className="button button-secondary"
            type="button"
            onClick={onReset}
          >
            Edit another video
          </button>
        </div>
      </div>
    </section>
  );
}
