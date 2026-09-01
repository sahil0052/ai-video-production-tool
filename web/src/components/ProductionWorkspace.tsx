import { useEffect, useMemo, useState } from "react";

import {
  approveFinalProduction,
  approveProductionGeneration,
  assembleProductionJob,
  createProductionJob,
  decideFlowCandidate,
  getFlowCandidates,
  getProductionArtifactUrl,
  getProductionJob,
  getProductionVideoUrl,
  type FlowCandidatesResponse,
  type FlowReviewScores,
  type FlowShot,
  type ProductionJobRecord,
  type ProductionSettings,
} from "../api";

const POLL_MS = 2000;
const MAX_UPLOAD_BYTES = 250 * 1024 * 1024;
const ACTIVE_PRODUCTION_JOB_KEY = "cutline-active-production-job";
const flowScoreFields = [
  ["prompt_fidelity", "Prompt fidelity"],
  ["motion_quality", "Motion quality"],
  ["continuity", "Continuity"],
  ["composition", "Composition"],
  ["artifact_integrity", "Artifact integrity"],
  ["editorial_usefulness", "Editorial usefulness"],
] as const satisfies ReadonlyArray<
  readonly [keyof FlowReviewScores, string]
>;
const defaultFlowScores: FlowReviewScores = {
  prompt_fidelity: 4,
  motion_quality: 4,
  continuity: 4,
  composition: 4,
  artifact_integrity: 4,
  editorial_usefulness: 4,
};

const stageOrder = [
  "Blueprint",
  "Flow approval",
  "Candidate review",
  "Assembly",
  "Automated QC",
  "Final approval",
];

const relativeArtifactPath = (path: string) => {
  const normalized = path.replaceAll("\\", "/");
  for (const marker of [
    "flow-candidates/",
    "review/",
    "assets/",
  ]) {
    const index = normalized.lastIndexOf(marker);
    if (index >= 0) {
      return normalized.slice(index);
    }
  }
  return normalized.split("/").at(-1) ?? normalized;
};

const stateStage = (state: ProductionJobRecord["state"]) => {
  if (state === "analyzing" || state === "blueprint-ready") {
    return 0;
  }
  if (
    state === "awaiting-generation-approval" ||
    state === "generating"
  ) {
    return 1;
  }
  if (state === "awaiting-candidate-review") {
    return 2;
  }
  if (state === "assembling") {
    return 3;
  }
  if (state === "automated-review") {
    return 4;
  }
  return 5;
};

function ProductionUpload({
  busy,
  onSubmit,
}: {
  busy: boolean;
  onSubmit: (file: File, settings: ProductionSettings) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState<ProductionSettings>({
    primaryReference: 10,
    secondaryReference: 4,
    flowOperationBudget: 3,
  });

  const selectFile = (candidate?: File) => {
    if (!candidate) {
      return;
    }
    if (!candidate.name.toLowerCase().endsWith(".mp4")) {
      setError("Choose an MP4 video.");
      setFile(null);
      return;
    }
    if (candidate.size > MAX_UPLOAD_BYTES) {
      setError("The MP4 must be smaller than 250 MB.");
      setFile(null);
      return;
    }
    setError(null);
    setFile(candidate);
  };

  return (
    <section className="production-upload">
      <div className="production-hero">
        <p className="eyebrow">Flow-assisted production editor</p>
        <h1>Reference-matched editing, with human release gates.</h1>
        <p>
          Real product captures and direct evidence stay factual. Google Flow
          is restricted to short illustrative motion plates.
        </p>
        <div className="policy-row">
          <span>Original narration preserved</span>
          <span>Flow ≤ 22%</span>
          <span>No generated UI or evidence</span>
        </div>
      </div>

      <div className="production-setup-card">
        <label className="file-picker">
          <span>Raw portrait MP4</span>
          <strong>{file?.name ?? "Choose the source video"}</strong>
          <input
            aria-label="Choose production MP4 video"
            name="source-video"
            type="file"
            accept="video/mp4,.mp4"
            disabled={busy}
            onChange={(event) => selectFile(event.target.files?.[0])}
          />
        </label>

        <div className="settings-grid">
          <label>
            <span>Primary reference</span>
            <select
              name="primary-reference"
              value={settings.primaryReference}
              onChange={(event) =>
                setSettings({
                  ...settings,
                  primaryReference: Number(event.target.value),
                })
              }
            >
              <option value={10}>Reference 10 — technical</option>
              <option value={4}>Reference 4 — documentary</option>
            </select>
          </label>
          <label>
            <span>Secondary reference</span>
            <select
              name="secondary-reference"
              value={settings.secondaryReference}
              onChange={(event) =>
                setSettings({
                  ...settings,
                  secondaryReference: Number(event.target.value),
                })
              }
            >
              <option value={4}>Reference 4 — risk sequence</option>
              <option value={10}>Reference 10 — technical</option>
            </select>
          </label>
          <label>
            <span>Paid Flow operation cap</span>
            <select
              name="flow-operation-budget"
              value={settings.flowOperationBudget}
              onChange={(event) =>
                setSettings({
                  ...settings,
                  flowOperationBudget: Number(event.target.value),
                })
              }
            >
              <option value={3}>3 operations — cheapest</option>
              <option value={4}>4 operations — one retry</option>
              <option value={5}>5 operations — two retries</option>
              <option value={0}>0 operations — planning only</option>
            </select>
          </label>
        </div>

        <div className="production-assumptions">
          <div>
            <small>Quality target</small>
            <strong>Reference maximum</strong>
          </div>
          <div>
            <small>Evidence policy</small>
            <strong>Evidence-first hybrid</strong>
          </div>
          <div>
            <small>Voice policy</small>
            <strong>Preserve verbatim</strong>
          </div>
        </div>

        {error ? <p className="form-error">{error}</p> : null}
        <button
          className="button button-primary production-start"
          type="button"
          disabled={!file || busy}
          onClick={() => file && onSubmit(file, settings)}
        >
          {busy ? "Building blueprint…" : "Build production blueprint"}
        </button>
        <p className="approval-note">
          Planning is free. Flow generation cannot start until you approve
          the operation count on the next screen.
        </p>
      </div>
    </section>
  );
}

function CandidateCard({
  jobId,
  shot,
  busy,
  onDecision,
}: {
  jobId: string;
  shot: FlowShot;
  busy: boolean;
  onDecision: () => Promise<void>;
}) {
  const latest = shot.attempts.at(-1);
  const review = latest?.result_json?.candidate_review;
  const [startMs, setStartMs] = useState(700);
  const [endMs, setEndMs] = useState(
    Math.min(2200, shot.end_ms - shot.start_ms),
  );
  const [scores, setScores] = useState<FlowReviewScores>(() => ({
    ...defaultFlowScores,
  }));
  const [speed, setSpeed] = useState(1);
  const [crop, setCrop] = useState(() => ({
    x: 0,
    y: 0,
    width: 1,
    height: 1,
  }));
  const [colorCorrection, setColorCorrection] = useState(() => ({
    brightness: 1,
    contrast: 1,
    saturation: 1,
  }));
  const [submitting, setSubmitting] = useState(false);
  const proxyPath = review?.proxy_path
    ? relativeArtifactPath(review.proxy_path)
    : null;
  const contactPath = review?.contact_sheet_path
    ? relativeArtifactPath(review.contact_sheet_path)
    : null;
  const scoreValues = Object.values(scores);
  const totalScore = scoreValues.reduce(
    (total, score) => total + score,
    0,
  );
  const scoreGatePassed =
    totalScore >= 24 && scoreValues.every((score) => score >= 3);
  const cropIsValid =
    crop.x >= 0 &&
    crop.y >= 0 &&
    crop.width > 0 &&
    crop.height > 0 &&
    crop.x + crop.width <= 1 &&
    crop.y + crop.height <= 1;

  const decide = async (accepted: boolean) => {
    if (!latest) {
      return;
    }
    setSubmitting(true);
    try {
      await decideFlowCandidate(jobId, {
        shotId: shot.id,
        attempt: latest.attempt,
        accepted,
        acceptedStartMs: accepted ? startMs : undefined,
        acceptedEndMs: accepted ? endMs : undefined,
        rejectionReasons: accepted
          ? []
          : ["Rejected during human editorial review"],
        scores,
        speed,
        crop,
        colorCorrection,
      });
      await onDecision();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <article className="candidate-card">
      <div className="candidate-heading">
        <div>
          <small>{shot.editorial_role.replaceAll("-", " ")}</small>
          <h3>{shot.id.replace("flow-", "").replaceAll("-", " ")}</h3>
        </div>
        <span data-status={shot.status}>{shot.status}</span>
      </div>
      {proxyPath ? (
        <video
          controls
          muted
          playsInline
          src={getProductionArtifactUrl(jobId, proxyPath)}
        />
      ) : (
        <div className="candidate-empty">Generation not submitted yet.</div>
      )}
      <p className="candidate-prompt">{shot.prompt}</p>
      {contactPath ? (
        <a
          className="artifact-link"
          href={getProductionArtifactUrl(jobId, contactPath)}
          target="_blank"
          rel="noreferrer"
        >
          Inspect eight-frame contact sheet
        </a>
      ) : null}
      {latest && shot.status !== "accepted" ? (
        <>
          <div className="candidate-scorecard">
            <div className="candidate-score-heading">
              <span>Human review score</span>
              <strong data-passed={scoreGatePassed}>
                {totalScore}/30
              </strong>
            </div>
            <div className="score-controls">
              {flowScoreFields.map(([key, label]) => (
                <label key={key}>
                  <span>{label}</span>
                  <select
                    aria-label={`${label} score`}
                    name={`${shot.id}-${key}-score`}
                    value={scores[key]}
                    onChange={(event) =>
                      setScores((current) => ({
                        ...current,
                        [key]: Number(event.target.value),
                      }))
                    }
                  >
                    {[1, 2, 3, 4, 5].map((score) => (
                      <option key={score} value={score}>
                        {score}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
            <small>
              Acceptance requires 24/30 and no score below 3.
            </small>
          </div>
          <div className="window-controls">
            <label>
              <span>Start ms</span>
              <input
                name={`${shot.id}-accepted-start-ms`}
                type="number"
                min={0}
                value={startMs}
                onChange={(event) => setStartMs(Number(event.target.value))}
              />
            </label>
            <label>
              <span>End ms</span>
              <input
                name={`${shot.id}-accepted-end-ms`}
                type="number"
                min={700}
                max={12000}
                value={endMs}
                onChange={(event) => setEndMs(Number(event.target.value))}
              />
            </label>
          </div>
          <div className="adjustment-controls">
            <label>
              <span>Playback speed</span>
              <input
                aria-label="Flow playback speed"
                name={`${shot.id}-playback-speed`}
                type="number"
                min={0.5}
                max={2}
                step={0.05}
                value={speed}
                onChange={(event) =>
                  setSpeed(Number(event.target.value))
                }
              />
            </label>
            {(
              [
                ["brightness", "Flow brightness"],
                ["contrast", "Flow contrast"],
                ["saturation", "Flow saturation"],
              ] as const
            ).map(([key, label]) => (
              <label key={key}>
                <span>{label.replace("Flow ", "")}</span>
                <input
                  aria-label={label}
                  name={`${shot.id}-${key}`}
                  type="number"
                  min={key === "saturation" ? 0 : 0.5}
                  max={key === "saturation" ? 2 : 1.5}
                  step={0.05}
                  value={colorCorrection[key]}
                  onChange={(event) =>
                    setColorCorrection((current) => ({
                      ...current,
                      [key]: Number(event.target.value),
                    }))
                  }
                />
              </label>
            ))}
          </div>
          <div className="adjustment-controls crop-controls">
            {(
              [
                ["x", "Flow crop X"],
                ["y", "Flow crop Y"],
                ["width", "Flow crop width"],
                ["height", "Flow crop height"],
              ] as const
            ).map(([key, label]) => (
              <label key={key}>
                <span>{label.replace("Flow ", "")}</span>
                <input
                  aria-label={label}
                  name={`${shot.id}-crop-${key}`}
                  type="number"
                  min={0}
                  max={1}
                  step={0.01}
                  value={crop[key]}
                  onChange={(event) =>
                    setCrop((current) => ({
                      ...current,
                      [key]: Number(event.target.value),
                    }))
                  }
                />
              </label>
            ))}
          </div>
          <div className="candidate-actions">
            <button
              className="button button-secondary"
              type="button"
              disabled={busy || submitting}
              onClick={() => void decide(false)}
            >
              Reject
            </button>
            <button
              className="button button-primary"
              type="button"
              disabled={
                busy ||
                submitting ||
                review?.hard_gate_passed !== true ||
                !scoreGatePassed ||
                !cropIsValid ||
                endMs - startMs < 700 ||
                endMs - startMs > 2200
              }
              onClick={() => void decide(true)}
            >
              Accept window
            </button>
          </div>
        </>
      ) : null}
    </article>
  );
}

function ProductionDashboard({
  job,
  candidates,
  busy,
  onGenerate,
  onRefresh,
  onAssemble,
  onFinalApprove,
  onReset,
}: {
  job: ProductionJobRecord;
  candidates: FlowCandidatesResponse | null;
  busy: boolean;
  onGenerate: () => Promise<void>;
  onRefresh: () => Promise<void>;
  onAssemble: () => Promise<void>;
  onFinalApprove: () => Promise<void>;
  onReset: () => void;
}) {
  const stage = stateStage(job.state);
  const allAccepted =
    candidates != null &&
    candidates.shots.length > 0 &&
    candidates.shots.every((shot) => shot.status === "accepted");
  const operationsRemain =
    job.consumed_paid_operations < job.flow_operation_budget;
  const artifact = (key: string, fallback: string) =>
    job.artifacts[key] ?? fallback;

  return (
    <section className="production-dashboard">
      <div className="production-topline">
        <div>
          <p className="eyebrow">Production job</p>
          <h1>{job.state.replaceAll("-", " ")}</h1>
        </div>
        <div className="budget-meter">
          <small>Flow operations</small>
          <strong>
            {job.consumed_paid_operations} / {job.flow_operation_budget}
          </strong>
        </div>
      </div>

      <ol className="production-stages">
        {stageOrder.map((label, index) => (
          <li
            key={label}
            data-status={
              index < stage
                ? "complete"
                : index === stage
                  ? "active"
                  : "pending"
            }
          >
            <span>{index + 1}</span>
            {label}
          </li>
        ))}
      </ol>

      {job.error ? (
        <div className="production-alert" role="alert">
          {job.error}
        </div>
      ) : null}

      <div className="production-grid">
        <aside className="review-sidebar">
          <h2>Blueprint review</h2>
          <p>
            Inspect the shot structure and evidence before any paid
            generation.
          </p>
          <div className="artifact-list">
            {[
              ["Storyboard", artifact("storyboard", "storyboard.json")],
              ["Evidence", artifact("evidence", "evidence.json")],
              ["Caption plan", artifact("caption_plan", "caption-plan.json")],
              ["Flow shot plan", artifact("flow_shot_plan", "flow-shot-plan.json")],
              ["Asset provenance", artifact("asset_manifest", "asset-manifest.json")],
            ].map(([label, path]) => (
              <a
                key={label}
                href={getProductionArtifactUrl(job.id, path)}
                target="_blank"
                rel="noreferrer"
              >
                <span>{label}</span>
                <b>Open</b>
              </a>
            ))}
          </div>

          {job.state === "awaiting-generation-approval" ? (
            <div className="approval-card">
              <small>Explicit paid action</small>
              <h3>
                Approve up to {job.flow_operation_budget} Flow operations
              </h3>
              <p>
                The editor submits one portrait Veo Lite candidate at a time.
                It never retries a known media ID.
              </p>
              <button
                className="button button-primary"
                type="button"
                disabled={busy || job.flow_operation_budget === 0}
                onClick={() => void onGenerate()}
              >
                Approve generation
              </button>
            </div>
          ) : null}

          {job.state === "awaiting-candidate-review" &&
          operationsRemain &&
          !allAccepted ? (
            <button
              className="button button-secondary sidebar-action"
              type="button"
              disabled={busy}
              onClick={() => void onGenerate()}
            >
              Generate remaining / retry
            </button>
          ) : null}

          {job.state === "awaiting-candidate-review" && allAccepted ? (
            <button
              className="button button-primary sidebar-action"
              type="button"
              disabled={busy}
              onClick={() => void onAssemble()}
            >
              Assemble production edit
            </button>
          ) : null}

          {job.state === "blueprint-ready" ? (
            <button
              className="button button-primary sidebar-action"
              type="button"
              disabled={busy}
              onClick={() => void onAssemble()}
            >
              Assemble production edit
            </button>
          ) : null}

          {job.state === "completed" ? (
            <button
              className="button button-secondary sidebar-action"
              type="button"
              onClick={onReset}
            >
              Start another production
            </button>
          ) : null}
        </aside>

        <div className="production-main">
          {job.state === "generating" ||
          job.state === "assembling" ||
          job.state === "automated-review" ? (
            <div className="production-wait">
              <span />
              <h2>Production work is running.</h2>
              <p>
                This stage is sequential and resumable. Paid operations are
                recorded before another submission can occur.
              </p>
            </div>
          ) : null}

          {candidates && candidates.shots.length > 0 ? (
            <div className="candidate-section">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Human candidate gate</p>
                  <h2>Flow motion plates</h2>
                </div>
                <span>
                  {candidates.shots.filter((shot) => shot.status === "accepted").length}
                  /{candidates.shots.length} accepted
                </span>
              </div>
              <div className="candidate-grid">
                {candidates.shots.map((shot) => (
                  <CandidateCard
                    key={shot.id}
                    jobId={job.id}
                    shot={shot}
                    busy={busy}
                    onDecision={onRefresh}
                  />
                ))}
              </div>
            </div>
          ) : null}

          {job.state === "awaiting-final-approval" ||
          job.state === "completed" ? (
            <div className="final-review">
              <div className="final-video">
                <video
                  controls
                  playsInline
                  src={
                    job.state === "completed"
                      ? getProductionVideoUrl(job.id)
                      : getProductionArtifactUrl(job.id, "edited.mp4")
                  }
                />
              </div>
              <div className="final-review-copy">
                <p className="eyebrow">Final release gate</p>
                <h2>Compare, inspect, then release.</h2>
                <p>
                  Automation has checked pacing, source coverage, captions,
                  narration continuity, loudness, evidence OCR and visual
                  diversity. Human approval remains mandatory.
                </p>
                <div className="artifact-list compact">
                  <a
                    href={getProductionArtifactUrl(
                      job.id,
                      "review/reference-comparison-v4.jpg",
                    )}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <span>Reference comparison</span>
                    <b>Open</b>
                  </a>
                  <a
                    href={getProductionArtifactUrl(job.id, "review-report.json")}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <span>Automated QC report</span>
                    <b>Open</b>
                  </a>
                  <a
                    href={getProductionArtifactUrl(job.id, "frame-audit.json")}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <span>Frame audit</span>
                    <b>Open</b>
                  </a>
                </div>
                {job.state === "awaiting-final-approval" ? (
                  <button
                    className="button button-primary final-approve"
                    type="button"
                    disabled={busy || !job.automated_pass}
                    onClick={() => void onFinalApprove()}
                  >
                    Approve final release
                  </button>
                ) : (
                  <a
                    className="button button-primary final-approve"
                    href={getProductionVideoUrl(job.id)}
                    download
                  >
                    Download approved MP4
                  </a>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

export function ProductionWorkspace() {
  const [job, setJob] = useState<ProductionJobRecord | null>(null);
  const [candidates, setCandidates] =
    useState<FlowCandidatesResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const savedJobId = window.localStorage.getItem(
      ACTIVE_PRODUCTION_JOB_KEY,
    );
    if (!savedJobId) {
      return;
    }
    let cancelled = false;
    setBusy(true);
    void (async () => {
      try {
        const restored = await getProductionJob(savedJobId);
        if (cancelled) {
          return;
        }
        setJob(restored);
        try {
          setCandidates(await getFlowCandidates(savedJobId));
        } catch {
          setCandidates(null);
        }
      } catch (restoreError) {
        window.localStorage.removeItem(ACTIVE_PRODUCTION_JOB_KEY);
        if (!cancelled) {
          setError(
            restoreError instanceof Error
              ? restoreError.message
              : "Unable to restore the saved production job.",
          );
        }
      } finally {
        if (!cancelled) {
          setBusy(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const shouldPoll = useMemo(
    () =>
      job != null &&
      ["analyzing", "generating", "assembling", "automated-review"].includes(
        job.state,
      ),
    [job],
  );

  const refresh = async () => {
    if (!job) {
      return;
    }
    const next = await getProductionJob(job.id);
    setJob(next);
    try {
      setCandidates(await getFlowCandidates(job.id));
    } catch {
      setCandidates(null);
    }
  };

  useEffect(() => {
    if (!shouldPoll || !job) {
      return;
    }
    const timer = window.setTimeout(() => {
      void refresh().catch((refreshError) =>
        setError(
          refreshError instanceof Error
            ? refreshError.message
            : "Unable to refresh production status.",
        ),
      );
    }, POLL_MS);
    return () => window.clearTimeout(timer);
  }, [job, shouldPoll]);

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await refresh();
    } catch (actionError) {
      setError(
        actionError instanceof Error
          ? actionError.message
          : "The production action failed.",
      );
    } finally {
      setBusy(false);
    }
  };

  if (!job) {
    return (
      <>
        {error ? (
          <div className="production-alert" role="alert">
            {error}
          </div>
        ) : null}
        <ProductionUpload
          busy={busy}
          onSubmit={(file, settings) => {
            setBusy(true);
            setError(null);
            void createProductionJob(file, settings)
              .then(async (created) => {
                window.localStorage.setItem(
                  ACTIVE_PRODUCTION_JOB_KEY,
                  created.id,
                );
                setJob(created);
                setCandidates(await getFlowCandidates(created.id));
              })
              .catch((uploadError) =>
                setError(
                  uploadError instanceof Error
                    ? uploadError.message
                    : "Unable to build the production blueprint.",
                ),
              )
              .finally(() => setBusy(false));
          }}
        />
      </>
    );
  }

  return (
    <>
      {error ? (
        <div className="production-alert" role="alert">
          {error}
        </div>
      ) : null}
      <ProductionDashboard
        job={job}
        candidates={candidates}
        busy={busy}
        onGenerate={() =>
          run(() =>
            approveProductionGeneration(
              job.id,
              job.flow_operation_budget,
            ),
          )
        }
        onRefresh={async () => {
          await refresh();
        }}
        onAssemble={() => run(() => assembleProductionJob(job.id))}
        onFinalApprove={() =>
          run(() => approveFinalProduction(job.id))
        }
        onReset={() => {
          window.localStorage.removeItem(ACTIVE_PRODUCTION_JOB_KEY);
          setJob(null);
          setCandidates(null);
          setError(null);
        }}
      />
    </>
  );
}
