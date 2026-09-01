import { useEffect, useState } from "react";

import { createJob, getJob, getVideoUrl, type JobRecord } from "./api";
import { ProcessingView } from "./components/ProcessingView";
import { ProductionWorkspace } from "./components/ProductionWorkspace";
import { ResultView } from "./components/ResultView";
import { UploadPanel } from "./components/UploadPanel";

const JOB_POLL_INTERVAL_MS = 2000;

function FastEditor() {
  const [job, setJob] = useState<JobRecord | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!job || job.state === "completed" || job.state === "failed") {
      return;
    }
    const timer = window.setTimeout(async () => {
      try {
        setJob(await getJob(job.id));
      } catch (pollError) {
        setError(
          pollError instanceof Error
            ? pollError.message
            : "Unable to read the processing status.",
        );
      }
    }, JOB_POLL_INTERVAL_MS);
    return () => window.clearTimeout(timer);
  }, [job]);

  useEffect(
    () => () => {
      if (previewUrl.startsWith("blob:")) {
        URL.revokeObjectURL(previewUrl);
      }
    },
    [previewUrl],
  );

  const handleUpload = async (selected: File) => {
    setUploading(true);
    setError(null);
    setFile(selected);
    if (previewUrl.startsWith("blob:")) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(
      typeof URL.createObjectURL === "function"
        ? URL.createObjectURL(selected)
        : "",
    );
    try {
      setJob(await createJob(selected));
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "The upload could not be started.",
      );
    } finally {
      setUploading(false);
    }
  };

  const reset = () => {
    if (previewUrl.startsWith("blob:")) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl("");
    setJob(null);
    setFile(null);
    setError(null);
    setUploading(false);
  };

  const failedMessage =
    error ||
    (job?.state === "failed" ? job.error || "Editing failed." : null);

  return failedMessage ? (
    <section className="error-state" role="alert">
      <p>Something interrupted the edit.</p>
      <h1>{failedMessage}</h1>
      <button className="button button-primary" type="button" onClick={reset}>
        Start again
      </button>
    </section>
  ) : job?.state === "completed" && job.result ? (
    <ResultView
      filename={file?.name || job.original_filename}
      videoUrl={getVideoUrl(job.id)}
      captionCount={job.result.caption_count}
      cutCount={job.result.cut_timestamps.length}
      brollCoverage={job.result.broll_coverage}
      styleScore={job.result.style_score}
      qcPassed={job.result.qc_passed}
      onReset={reset}
    />
  ) : job && file ? (
    <ProcessingView
      filename={file.name}
      previewUrl={previewUrl}
      state={job.state}
      progress={job.progress}
    />
  ) : (
    <UploadPanel busy={uploading} onUpload={handleUpload} />
  );
}

export function App() {
  const [mode, setMode] = useState<"production" | "fast">("production");

  return (
    <div className="app-shell app-shell-wide">
      <header className="app-header">
        <a
          className="brand"
          href="/"
          onClick={(event) => event.preventDefault()}
        >
          <span className="brand-mark" aria-hidden="true">
            <i />
            <i />
          </span>
          Cutline
        </a>
        <div className="mode-switch" aria-label="Editor mode">
          <button
            type="button"
            data-active={mode === "production"}
            onClick={() => setMode("production")}
          >
            Production V4
          </button>
          <button
            type="button"
            data-active={mode === "fast"}
            onClick={() => setMode("fast")}
          >
            Fast edit
          </button>
        </div>
        <div className="header-status">
          <span aria-hidden="true" />
          Local media workspace
        </div>
      </header>

      <main
        className={mode === "production" ? "production-main-shell" : ""}
      >
        {mode === "production" ? <ProductionWorkspace /> : <FastEditor />}
      </main>

      <footer className="app-footer">
        <span>Cutline local editor</span>
        <span>MP4 · 9:16 · staged human approval</span>
      </footer>
    </div>
  );
}
