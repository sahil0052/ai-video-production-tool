export type PipelineResult = {
  caption_count: number;
  cut_timestamps: number[];
  transcript_text: string;
  broll_coverage: number;
  style_score: number;
  qc_passed: boolean;
};

export type JobRecord = {
  id: string;
  original_filename: string;
  state: string;
  progress: number;
  error: string | null;
  result: PipelineResult | null;
};

export type ProductionState =
  | "analyzing"
  | "blueprint-ready"
  | "awaiting-generation-approval"
  | "generating"
  | "awaiting-candidate-review"
  | "assembling"
  | "automated-review"
  | "awaiting-final-approval"
  | "completed";

export type ProductionJobRecord = {
  id: string;
  source_path: string;
  output_dir: string;
  state: ProductionState;
  primary_reference: number;
  secondary_reference: number;
  flow_operation_budget: number;
  approved_paid_operations: number;
  consumed_paid_operations: number;
  flow_profile: string;
  flow_project_id: string | null;
  artifacts: Record<string, string>;
  accepted_clips: Array<{
    shot_id: string;
    attempt: number;
    proxy_path: string;
    trim_start_ms: number;
    trim_end_ms: number;
  }>;
  automated_pass: boolean;
  human_approved: boolean;
  final_reviewer: string | null;
  error: string | null;
};

export type ProductionSettings = {
  primaryReference: number;
  secondaryReference: number;
  flowOperationBudget: number;
};

export type FlowCandidateAttempt = {
  attempt: number;
  media_id: string | null;
  result_json: {
    candidate_review?: {
      proxy_path?: string;
      contact_sheet_path?: string;
      automated_report_path?: string;
      hard_gate_passed?: boolean;
    };
  } | null;
};

export type FlowShot = {
  id: string;
  start_ms: number;
  end_ms: number;
  editorial_role: string;
  prompt: string;
  constraints: string[];
  attempts: FlowCandidateAttempt[];
  status: string;
};

export type FlowCandidatesResponse = {
  shots: FlowShot[];
  accepted_clips: ProductionJobRecord["accepted_clips"];
};

export type FlowReviewScores = {
  prompt_fidelity: number;
  motion_quality: number;
  continuity: number;
  composition: number;
  artifact_integrity: number;
  editorial_usefulness: number;
};


export async function createJob(_file: File): Promise<JobRecord> {
  const body = new FormData();
  body.append("file", _file);
  const response = await fetch("/api/jobs", {
    method: "POST",
    body
  });
  return parseJobResponse(response);
}


export async function getJob(_jobId: string): Promise<JobRecord> {
  const response = await fetch(`/api/jobs/${encodeURIComponent(_jobId)}`);
  return parseJobResponse(response);
}

export async function createProductionJob(
  file: File,
  settings: ProductionSettings,
): Promise<ProductionJobRecord> {
  const body = new FormData();
  body.append("file", file);
  body.append(
    "primary_reference",
    String(settings.primaryReference),
  );
  body.append(
    "secondary_reference",
    String(settings.secondaryReference),
  );
  body.append(
    "flow_operation_budget",
    String(settings.flowOperationBudget),
  );
  body.append("asset_policy", "free-licensed");
  body.append("quality_target", "reference-max");
  body.append("capture_profile", "local-metatrader");
  body.append("voice_policy", "preserve-verbatim");
  return parseJsonResponse(
    await fetch("/api/production/jobs", {
      method: "POST",
      body,
    }),
  );
}

export async function getProductionJob(
  jobId: string,
): Promise<ProductionJobRecord> {
  return parseJsonResponse(
    await fetch(`/api/production/jobs/${encodeURIComponent(jobId)}`),
  );
}

export async function getFlowCandidates(
  jobId: string,
): Promise<FlowCandidatesResponse> {
  return parseJsonResponse(
    await fetch(
      `/api/production/jobs/${encodeURIComponent(jobId)}/flow-candidates`,
    ),
  );
}

export async function approveProductionGeneration(
  jobId: string,
  approvePaidOps: number,
): Promise<ProductionJobRecord> {
  return parseJsonResponse(
    await fetch(
      `/api/production/jobs/${encodeURIComponent(jobId)}/generation-approval`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approve_paid_ops: approvePaidOps }),
      },
    ),
  );
}

export async function decideFlowCandidate(
  jobId: string,
  decision: {
    shotId: string;
    attempt: number;
    accepted: boolean;
    acceptedStartMs?: number;
    acceptedEndMs?: number;
    rejectionReasons?: string[];
    scores: FlowReviewScores;
    speed?: number;
    crop?: {
      x: number;
      y: number;
      width: number;
      height: number;
    };
    colorCorrection?: {
      brightness: number;
      contrast: number;
      saturation: number;
    };
  },
): Promise<Record<string, unknown>> {
  return parseJsonResponse(
    await fetch(
      `/api/production/jobs/${encodeURIComponent(jobId)}/candidate-decisions`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          shot_id: decision.shotId,
          attempt: decision.attempt,
          accepted: decision.accepted,
          scores: decision.scores,
          accepted_start_ms: decision.acceptedStartMs ?? null,
          accepted_end_ms: decision.acceptedEndMs ?? null,
          reviewer: "user",
          rejection_reasons: decision.rejectionReasons ?? [],
          speed: decision.speed ?? 1,
          crop: decision.crop ?? {
            x: 0,
            y: 0,
            width: 1,
            height: 1,
          },
          color_correction: decision.colorCorrection ?? {
            brightness: 1,
            contrast: 1,
            saturation: 1,
          },
        }),
      },
    ),
  );
}

export async function assembleProductionJob(
  jobId: string,
): Promise<ProductionJobRecord> {
  return parseJsonResponse(
    await fetch(
      `/api/production/jobs/${encodeURIComponent(jobId)}/assemble`,
      { method: "POST" },
    ),
  );
}

export async function approveFinalProduction(
  jobId: string,
): Promise<ProductionJobRecord> {
  return parseJsonResponse(
    await fetch(
      `/api/production/jobs/${encodeURIComponent(jobId)}/final-approval`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reviewer: "user" }),
      },
    ),
  );
}

export function getProductionArtifactUrl(
  jobId: string,
  path: string,
): string {
  const encoded = path
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/");
  return `/api/production/jobs/${encodeURIComponent(jobId)}/artifacts/${encoded}`;
}

export function getProductionVideoUrl(jobId: string): string {
  return `/api/production/jobs/${encodeURIComponent(jobId)}/video`;
}


export function getVideoUrl(jobId: string): string {
  return `/api/jobs/${jobId}/video`;
}


async function parseJobResponse(response: Response): Promise<JobRecord> {
  return parseJsonResponse(response);
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed with status ${response.status}.`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // Keep the status-based fallback when a proxy returns non-JSON.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}
