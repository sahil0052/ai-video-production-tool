import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";

import * as api from "../api";
import { ProductionWorkspace } from "./ProductionWorkspace";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    createProductionJob: vi.fn(),
    getProductionJob: vi.fn(),
    getFlowCandidates: vi.fn(),
    approveProductionGeneration: vi.fn(),
    decideFlowCandidate: vi.fn(),
  };
});

afterEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
});

test("names every production setup form control", () => {
  render(<ProductionWorkspace />);

  const fileInput = screen.getByLabelText("Choose production MP4 video");
  const selects = screen.getAllByRole("combobox");
  for (const control of [fileInput, ...selects]) {
    expect(control).toHaveAttribute("name");
    expect(control.getAttribute("name")).not.toBe("");
  }
});

test("shows blueprint review and explicit paid approval after planning", async () => {
  const job: api.ProductionJobRecord = {
    id: "production-id",
    source_path: "D:/Downloads/0806.mp4",
    output_dir: "C:/deliverables/0806-production-v4",
    state: "awaiting-generation-approval",
    primary_reference: 10,
    secondary_reference: 4,
    flow_operation_budget: 3,
    approved_paid_operations: 0,
    consumed_paid_operations: 0,
    flow_profile: "sahilsharmabybit2",
    flow_project_id: null,
    artifacts: {
      storyboard: "storyboard.json",
      evidence: "evidence.json",
      flow_shot_plan: "flow-shot-plan.json",
    },
    accepted_clips: [],
    automated_pass: false,
    human_approved: false,
    final_reviewer: null,
    error: null,
  };
  vi.mocked(api.createProductionJob).mockResolvedValue(job);
  vi.mocked(api.getFlowCandidates).mockResolvedValue({
    shots: [],
    accepted_clips: [],
  });

  render(<ProductionWorkspace />);
  fireEvent.change(screen.getByLabelText("Choose production MP4 video"), {
    target: {
      files: [new File(["video"], "0806.mp4", { type: "video/mp4" })],
    },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Build production blueprint" }),
  );

  expect(
    await screen.findByRole("heading", {
      name: "Approve up to 3 Flow operations",
    }),
  ).toBeInTheDocument();
  expect(screen.getByText("Storyboard")).toBeInTheDocument();
  expect(screen.getByText("Evidence")).toBeInTheDocument();
});

test("submits editable human review scores for a Flow candidate", async () => {
  const job: api.ProductionJobRecord = {
    id: "production-id",
    source_path: "D:/Downloads/0806.mp4",
    output_dir: "C:/deliverables/0806-production-v4",
    state: "awaiting-candidate-review",
    primary_reference: 10,
    secondary_reference: 4,
    flow_operation_budget: 3,
    approved_paid_operations: 1,
    consumed_paid_operations: 1,
    flow_profile: "sahilsharmabybit2",
    flow_project_id: "flow-project",
    artifacts: {
      storyboard: "storyboard.json",
      evidence: "evidence.json",
      flow_shot_plan: "flow-shot-plan.json",
    },
    accepted_clips: [],
    automated_pass: false,
    human_approved: false,
    final_reviewer: null,
    error: null,
  };
  const candidates: api.FlowCandidatesResponse = {
    shots: [
      {
        id: "flow-risk",
        start_ms: 21820,
        end_ms: 24320,
        editorial_role: "physical-risk",
        prompt: "A single physical-risk metaphor with no readable text.",
        constraints: ["No readable text"],
        attempts: [
          {
            attempt: 1,
            media_id: "media-id",
            result_json: {
              candidate_review: {
                proxy_path: "flow-candidates/proxies/risk.mp4",
                contact_sheet_path:
                  "flow-candidates/contact-sheets/risk.jpg",
                hard_gate_passed: true,
              },
            },
          },
        ],
        status: "awaiting-review",
      },
    ],
    accepted_clips: [],
  };
  vi.mocked(api.createProductionJob).mockResolvedValue(job);
  vi.mocked(api.getProductionJob).mockResolvedValue(job);
  vi.mocked(api.getFlowCandidates).mockResolvedValue(candidates);
  vi.mocked(api.decideFlowCandidate).mockResolvedValue({
    accepted: true,
  });

  render(<ProductionWorkspace />);
  fireEvent.change(screen.getByLabelText("Choose production MP4 video"), {
    target: {
      files: [new File(["video"], "0806.mp4", { type: "video/mp4" })],
    },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Build production blueprint" }),
  );

  fireEvent.change(
    await screen.findByLabelText("Prompt fidelity score"),
    { target: { value: "5" } },
  );
  for (const control of [
    ...screen.getAllByRole("combobox"),
    ...screen.getAllByRole("spinbutton"),
  ]) {
    expect(control).toHaveAttribute("name");
    expect(control.getAttribute("name")).not.toBe("");
  }
  fireEvent.change(screen.getByLabelText("Motion quality score"), {
    target: { value: "3" },
  });
  fireEvent.change(screen.getByLabelText("Flow saturation"), {
    target: { value: "1.2" },
  });
  fireEvent.change(screen.getByLabelText("Flow crop X"), {
    target: { value: "0.05" },
  });
  fireEvent.change(screen.getByLabelText("Flow crop width"), {
    target: { value: "0.9" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Accept window" }),
  );

  await waitFor(() =>
    expect(api.decideFlowCandidate).toHaveBeenCalledWith(
      "production-id",
      expect.objectContaining({
        scores: {
          prompt_fidelity: 5,
          motion_quality: 3,
          continuity: 4,
          composition: 4,
          artifact_integrity: 4,
          editorial_usefulness: 4,
        },
        colorCorrection: {
          brightness: 1,
          contrast: 1,
          saturation: 1.2,
        },
        crop: {
          x: 0.05,
          y: 0,
          width: 0.9,
          height: 1,
        },
      }),
    ),
  );
});

test("restores an active staged production job after reload", async () => {
  const job: api.ProductionJobRecord = {
    id: "00000000-0000-4000-8000-000000000004",
    source_path: "D:/Downloads/0806.mp4",
    output_dir: "C:/deliverables/0806-production-v4",
    state: "awaiting-generation-approval",
    primary_reference: 10,
    secondary_reference: 4,
    flow_operation_budget: 3,
    approved_paid_operations: 0,
    consumed_paid_operations: 0,
    flow_profile: "sahilsharmabybit2",
    flow_project_id: null,
    artifacts: {
      storyboard: "storyboard.json",
      evidence: "evidence.json",
      flow_shot_plan: "flow-shot-plan.json",
    },
    accepted_clips: [],
    automated_pass: false,
    human_approved: false,
    final_reviewer: null,
    error: null,
  };
  window.localStorage.setItem(
    "cutline-active-production-job",
    job.id,
  );
  vi.mocked(api.getProductionJob).mockResolvedValue(job);
  vi.mocked(api.getFlowCandidates).mockResolvedValue({
    shots: [],
    accepted_clips: [],
  });

  render(<ProductionWorkspace />);

  expect(
    await screen.findByRole("heading", {
      name: "awaiting generation approval",
    }),
  ).toBeInTheDocument();
  expect(api.getProductionJob).toHaveBeenCalledWith(job.id);
});
