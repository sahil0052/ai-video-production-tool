import { act, fireEvent, render, screen } from "@testing-library/react";

import { App } from "./App";
import * as api from "./api";

vi.mock("./api", () => ({
  createJob: vi.fn(),
  getJob: vi.fn(),
  getVideoUrl: vi.fn((id: string) => `/api/jobs/${id}/video`),
  createProductionJob: vi.fn(),
  getProductionJob: vi.fn(),
  getFlowCandidates: vi.fn(),
  approveProductionGeneration: vi.fn(),
  decideFlowCandidate: vi.fn(),
  assembleProductionJob: vi.fn(),
  approveFinalProduction: vi.fn(),
  getProductionArtifactUrl: vi.fn(
    (id: string, path: string) =>
      `/api/production/jobs/${id}/artifacts/${path}`,
  ),
  getProductionVideoUrl: vi.fn(
    (id: string) => `/api/production/jobs/${id}/video`,
  ),
}));

afterEach(() => {
  vi.clearAllMocks();
  vi.useRealTimers();
});


test("moves from upload to processing after a valid submission", async () => {
  vi.mocked(api.createJob).mockResolvedValue({
    id: "job-id",
    original_filename: "0806.mp4",
    state: "queued",
    progress: 2,
    error: null,
    result: null
  });
  vi.mocked(api.getJob).mockResolvedValue({
    id: "job-id",
    original_filename: "0806.mp4",
    state: "queued",
    progress: 2,
    error: null,
    result: null
  });
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Fast edit" }));
  const input = screen.getByLabelText("Choose raw MP4 video");
  fireEvent.change(input, {
    target: {
      files: [new File(["video"], "0806.mp4", { type: "video/mp4" })]
    }
  });

  fireEvent.click(screen.getByRole("button", { name: "Edit this video" }));

  expect(
    await screen.findByRole("heading", { name: "Preparing your upload" })
  ).toBeInTheDocument();
});


test("does not poll a processing job more than once every two seconds", async () => {
  vi.useFakeTimers();
  const queuedJob = {
    id: "job-id",
    original_filename: "0806.mp4",
    state: "queued",
    progress: 2,
    error: null,
    result: null
  };
  vi.mocked(api.createJob).mockResolvedValue(queuedJob);
  vi.mocked(api.getJob).mockResolvedValue(queuedJob);
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Fast edit" }));
  fireEvent.change(screen.getByLabelText("Choose raw MP4 video"), {
    target: {
      files: [new File(["video"], "0806.mp4", { type: "video/mp4" })]
    }
  });

  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Edit this video" }));
  });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1900);
  });

  expect(api.getJob).not.toHaveBeenCalled();
});


test("defaults to the staged Production V4 workspace", () => {
  render(<App />);

  expect(
    screen.getByRole("heading", {
      name: "Reference-matched editing, with human release gates.",
    }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Production V4" }),
  ).toHaveAttribute("data-active", "true");
});
