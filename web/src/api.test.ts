import {
  createJob,
  createProductionJob,
  decideFlowCandidate,
  getJob,
} from "./api";


test("createJob uploads an MP4 and returns the job record", async () => {
  const job = {
    id: "job-id",
    original_filename: "0806.mp4",
    state: "queued",
    progress: 2,
    error: null,
    result: null
  };
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(job), {
        status: 202,
        headers: { "Content-Type": "application/json" }
      })
    )
  );

  const result = await createJob(
    new File(["video"], "0806.mp4", { type: "video/mp4" })
  );

  expect(result).toEqual(job);
  expect(fetch).toHaveBeenCalledWith(
    "/api/jobs",
    expect.objectContaining({ method: "POST" })
  );
});


test("getJob exposes API error details", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Job not found." }), {
        status: 404,
        headers: { "Content-Type": "application/json" }
      })
    )
  );

  await expect(getJob("missing")).rejects.toThrow("Job not found.");
});


test("createProductionJob sends locked V4 production settings", async () => {
  const job = {
    id: "production-id",
    state: "awaiting-generation-approval",
  };
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(job), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );

  await createProductionJob(
    new File(["video"], "0806.mp4", { type: "video/mp4" }),
    {
      primaryReference: 10,
      secondaryReference: 4,
      flowOperationBudget: 3,
    },
  );

  expect(fetch).toHaveBeenCalledWith(
    "/api/production/jobs",
    expect.objectContaining({ method: "POST" }),
  );
  const options = vi.mocked(fetch).mock.calls[0][1];
  const body = options?.body as FormData;
  expect(body.get("primary_reference")).toBe("10");
  expect(body.get("secondary_reference")).toBe("4");
  expect(body.get("flow_operation_budget")).toBe("3");
  expect(body.get("quality_target")).toBe("reference-max");
});

test("decideFlowCandidate sends the reviewer's six scores", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ accepted: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
  const scores = {
    prompt_fidelity: 5,
    motion_quality: 3,
    continuity: 4,
    composition: 5,
    artifact_integrity: 4,
    editorial_usefulness: 3,
  };

  await decideFlowCandidate("production-id", {
    shotId: "flow-risk",
    attempt: 1,
    accepted: true,
    acceptedStartMs: 700,
    acceptedEndMs: 2200,
    scores,
    speed: 1.1,
    crop: {
      x: 0.05,
      y: 0.1,
      width: 0.9,
      height: 0.8,
    },
    colorCorrection: {
      brightness: 1.05,
      contrast: 1.1,
      saturation: 1.2,
    },
  });

  const options = vi.mocked(fetch).mock.calls[0][1];
  const body = JSON.parse(String(options?.body));
  expect(body.scores).toEqual(scores);
  expect(body.speed).toBe(1.1);
  expect(body.crop).toEqual({
    x: 0.05,
    y: 0.1,
    width: 0.9,
    height: 0.8,
  });
  expect(body.color_correction).toEqual({
    brightness: 1.05,
    contrast: 1.1,
    saturation: 1.2,
  });
});
