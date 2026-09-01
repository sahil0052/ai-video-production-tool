import { useRef, useState } from "react";

type UploadPanelProps = {
  busy: boolean;
  onUpload: (file: File) => void;
};

const MAX_UPLOAD_BYTES = 250 * 1024 * 1024;


export function UploadPanel({ busy, onUpload }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const selectFile = (candidate: File | undefined) => {
    if (!candidate) {
      return;
    }
    if (!candidate.name.toLowerCase().endsWith(".mp4")) {
      setFile(null);
      setError("Choose an MP4 video file.");
      return;
    }
    if (candidate.size > MAX_UPLOAD_BYTES) {
      setFile(null);
      setError("The MP4 must be smaller than 250 MB.");
      return;
    }
    setError(null);
    setFile(candidate);
  };

  return (
    <section className="upload-layout" aria-labelledby="upload-heading">
      <div className="upload-copy">
        <h1 id="upload-heading">
          Drop the raw take.
          <br />
          Get the finished reel.
        </h1>
        <p>
          Built for vertical talking-head recordings under one minute. Your
          words stay intact; the rough edges do not.
        </p>
      </div>

      <div
        className={`drop-zone${dragging ? " is-dragging" : ""}`}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          selectFile(event.dataTransfer.files[0]);
        }}
      >
        <input
          ref={inputRef}
          className="visually-hidden"
          type="file"
          accept="video/mp4,.mp4"
          aria-label="Choose raw MP4 video"
          disabled={busy}
          onChange={(event) => selectFile(event.target.files?.[0])}
        />
        <div className="upload-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14.5v3A2.5 2.5 0 0 0 7.5 20h9a2.5 2.5 0 0 0 2.5-2.5v-3" />
          </svg>
        </div>
        <p className="drop-title">
          {file ? file.name : "Drag your raw MP4 here"}
        </p>
        <p className="drop-meta">
          {file
            ? `${(file.size / 1024 / 1024).toFixed(1)} MB · ready to edit`
            : "9:16 portrait · up to 65 seconds · 250 MB maximum"}
        </p>
        <div className="upload-actions">
          <button
            className="button button-secondary"
            type="button"
            disabled={busy}
            onClick={() => inputRef.current?.click()}
          >
            Choose video
          </button>
          {file ? (
            <button
              className="button button-primary"
              type="button"
              disabled={busy}
              onClick={() => onUpload(file)}
            >
              {busy ? "Uploading…" : "Edit this video"}
            </button>
          ) : null}
        </div>
        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}
      </div>

      <ol className="process-strip" aria-label="Editing workflow">
        <li>
          <span>01</span>
          <strong>Analyze</strong>
          <small>Speech, cuts and framing</small>
        </li>
        <li>
          <span>02</span>
          <strong>Clean</strong>
          <small>Audio, color and pacing</small>
        </li>
        <li>
          <span>03</span>
          <strong>Caption</strong>
          <small>Synced, readable subtitles</small>
        </li>
        <li>
          <span>04</span>
          <strong>Finish</strong>
          <small>Social-ready H.264 export</small>
        </li>
      </ol>
    </section>
  );
}
