type ProcessingViewProps = {
  filename: string;
  previewUrl: string;
  state: string;
  progress: number;
};

const stageLabels: Record<string, string> = {
  queued: "Preparing your upload",
  analyzing: "Analyzing framing and cuts",
  transcribing: "Transcribing speech",
  cleaning: "Tightening speech and pauses",
  planning: "Building the edit",
  sourcing: "Matching visuals and graphics",
  rendering: "Rendering the finished reel",
  mastering: "Mastering sound and color",
  quality_control: "Scoring the finished edit",
  verifying: "Checking the final export"
};


export function ProcessingView({
  filename,
  previewUrl,
  state,
  progress
}: ProcessingViewProps) {
  const activeLabel = stageLabels[state] ?? "Processing your video";

  return (
    <section className="workspace-grid processing-view" aria-live="polite">
      <div className="preview-stage">
        <div className="phone-frame">
          <video src={previewUrl} muted playsInline />
          <div className="scan-line" aria-hidden="true" />
        </div>
      </div>

      <div className="job-panel">
        <p className="file-label">{filename}</p>
        <h1>{activeLabel}</h1>
        <p className="job-copy">
          The recording stays local to this editor while each production stage
          completes.
        </p>

        <div className="progress-heading">
          <span>Overall progress</span>
          <strong>{progress}%</strong>
        </div>
        <div
          className="progress-track"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress}
        >
          <span style={{ width: `${progress}%` }} />
        </div>

        <ol className="stage-list">
          {Object.entries(stageLabels).map(([key, label]) => {
            const stages = Object.keys(stageLabels);
            const activeIndex = stages.indexOf(state);
            const itemIndex = stages.indexOf(key);
            const status =
              itemIndex < activeIndex
                ? "complete"
                : itemIndex === activeIndex
                  ? "active"
                  : "pending";
            return (
              <li key={key} data-status={status}>
                <span aria-hidden="true" />
                {label}
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
