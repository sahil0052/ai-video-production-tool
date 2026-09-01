# 0809 Visual Upgrade V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a visually stronger V2 of the 0809 reel using three reviewed Flow plates, animated evidence, upgraded deterministic graphics, and the verified V1 audio path.

**Architecture:** Seed a new V2 deliverable from the existing bespoke 0809 planner, then replace its schedule and explicit layers through a focused `reference_story_v2.py` module. Reuse the existing Flow state machine, candidate review, explicit-layer compiler, Remotion renderer, and V1 audio remaster/review helpers.

**Tech Stack:** Python 3.11, Pydantic production contracts, Pillow, OpenCV, FFmpeg, Remotion/React, gflow-cli with Veo 3.1 Lite.

---

### Task 1: Lock the V2 schedule and Flow policy

**Files:**
- Create: `server/app/editor/reference_story_v2.py`
- Create: `server/tests/test_reference_story_v2.py`

- [ ] **Step 1: Write schedule and policy tests**

```python
def test_v2_schedule_covers_story_and_adds_visual_resets():
    shots = build_0809_v2_schedule()
    assert shots[0]["start_ms"] == 0
    assert shots[-1]["end_ms"] == 50_833
    assert all(a["end_ms"] == b["start_ms"] for a, b in zip(shots, shots[1:]))
    assert 28 <= len(shots) <= 35
    assert max(shot["end_ms"] - shot["start_ms"] for shot in shots) <= 3_000


def test_v2_flow_shots_are_short_and_non_factual(tmp_path):
    shots = build_0809_v2_flow_shots(tmp_path)
    assert len(shots) == 3
    assert sum(shot.end_ms - shot.start_ms for shot in shots) <= 5_700
    assert all(shot.mode == "i2v" for shot in shots)
    assert all(shot.requested_content in (["physical-metaphor"], ["abstract-motion"]) for shot in shots)
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='server'
python -m pytest server/tests/test_reference_story_v2.py -q
```

Expected: failures because the V2 module does not exist.

- [ ] **Step 3: Implement the exact schedule and three `FlowShotSpec` records**

Create:

```python
STORY_DURATION_MS = 50_833

def build_0809_v2_schedule() -> list[dict[str, object]]:
    specs = [
        (0, 900, "presenter", "source-presenter", "hook-date"),
        (900, 2200, "deterministic-graphic", "graphic-order-lanes", "hook-orders"),
        (2200, 4500, "licensed-context", "licensed-mixkit-trader", "market-open"),
        (4500, 6800, "presenter", "source-presenter", "order-scale"),
        (6800, 9500, "licensed-context", "licensed-mixkit-forex-screen", "loss"),
        (9500, 11000, "presenter", "source-presenter", "question-reset"),
        (11000, 12800, "flow-illustrative", "flow-update-module", "software-update-flow"),
        (12800, 14800, "licensed-context", "licensed-mixkit-code", "software-update-code"),
        (14800, 15550, "direct-evidence", "evidence-sec-overview", "company-overview"),
        (15550, 16700, "direct-evidence", "evidence-sec-overview-highlight", "company-highlight"),
        (16700, 18600, "flow-illustrative", "flow-server-propagation", "server-propagation"),
        (18600, 20300, "deterministic-graphic", "graphic-eight-servers-v2", "missed-server"),
        (20300, 21150, "direct-evidence", "evidence-sec-email", "email-overview"),
        (21150, 22000, "direct-evidence", "evidence-sec-email-highlight", "email-highlight"),
        (22000, 23800, "presenter", "source-presenter", "error-emails"),
        (23800, 25600, "presenter", "source-presenter", "forex-lesson"),
        (25600, 27500, "deterministic-graphic", "graphic-incident-bridge", "forex-bridge"),
        (27500, 28350, "direct-evidence", "evidence-sec-deployment", "deployment-overview"),
        (28350, 29250, "direct-evidence", "evidence-sec-deployment-highlight", "deployment-highlight"),
        (29250, 30100, "deterministic-graphic", "graphic-repeat-timeline", "repeated-error"),
        (30100, 32100, "presenter", "source-presenter", "verification"),
        (32100, 33600, "direct-evidence", "evidence-sec-controls", "missing-controls"),
        (33600, 34900, "presenter", "source-presenter", "emergency-stop"),
        (34900, 36000, "presenter", "source-presenter", "brand-order-limits"),
        (36000, 37100, "presenter", "source-presenter", "brand-controlled-automation"),
        (37100, 38300, "presenter", "source-presenter", "brand-equity-protection"),
        (38300, 39800, "presenter", "source-presenter", "risk-reset"),
        (39800, 41800, "flow-illustrative", "flow-risk-containment", "risk-containment"),
        (41800, 42500, "presenter", "source-presenter", "damage-limited"),
        (42500, 45200, "presenter", "source-presenter", "cta-setup"),
        (45200, 47200, "deterministic-graphic", "graphic-control-recap", "cta-recap"),
        (47200, 50200, "presenter", "source-presenter", "cta-card"),
        (50_200, STORY_DURATION_MS, "presenter", "source-presenter", "clean-ending"),
    ]
    return [
        {
            "id": f"v2-shot-{index:02d}",
            "start_ms": start_ms,
            "end_ms": end_ms,
            "source_role": source_role,
            "asset_id": asset_id,
            "editorial_role": editorial_role,
            "reference_role": "primary-10",
        }
        for index, (
            start_ms,
            end_ms,
            source_role,
            asset_id,
            editorial_role,
        ) in enumerate(specs, start=1)
    ]
```

Create `FlowShotSpec` values for:

- `flow-update-module`, 11,000-12,800 ms.
- `flow-server-propagation`, 16,700-18,600 ms.
- `flow-risk-containment`, 39,800-41,800 ms.

Every prompt must repeat the no-text/no-UI/no-number/no-document constraints.

- [ ] **Step 4: Run the V2 tests and verify GREEN**

```powershell
$env:PYTHONPATH='server'
python -m pytest server/tests/test_reference_story_v2.py -q
```

Expected: all Task 1 tests pass.

### Task 2: Seed the V2 deliverable and generate deterministic assets

**Files:**
- Modify: `server/app/editor/reference_story_v2.py`
- Modify: `server/tests/test_reference_story_v2.py`
- Create at runtime: `storage/deliverables/0809-production-v2-visual-upgrade/`

- [ ] **Step 1: Write tests for the seeded job and assets**

```python
def test_v2_job_requests_generation_and_preserves_v1(tmp_path, monkeypatch):
    artifacts = build_reference_story_v2_blueprint(
        source=Path("D:/Downloads/0809.mp4"),
        output_dir=tmp_path,
        seed_builder=fake_v1_builder,
    )
    job = ProductionStore(tmp_path).load()
    assert job.state == "awaiting-generation-approval"
    assert job.flow_operation_budget == 5
    assert Path(artifacts["flow_shot_plan"]).is_file()
    assert len(ProductionBlueprint.model_validate_json(
        (tmp_path / "blueprint.json").read_text()
    ).flow_shots) == 3
```

- [ ] **Step 2: Run and verify RED**

```powershell
python -m pytest server/tests/test_reference_story_v2.py -q
```

- [ ] **Step 3: Implement seeding**

`build_reference_story_v2_blueprint()` must:

1. Call `build_reference_story_blueprint()` for V1-compatible evidence, audio,
   source proxy, licensed media, and provenance.
2. Generate V2 overlays and Flow start/end plates with Pillow.
3. Replace the V1 schedule, layers, storyboard, and blueprint.
4. Set the job ID to `production-0809-visual-upgrade-v2`.
5. Set `flow_operation_budget=5`, the configured repository, profile
   `sahilsharmabybit2`, and state `awaiting-generation-approval`.
6. Write `flow-shot-plan.json`, `flow-instructions.json`, and an updated asset
   manifest with checksums.

- [ ] **Step 4: Run tests and verify GREEN**

```powershell
python -m pytest server/tests/test_reference_story_v2.py -q
```

### Task 3: Add the V2 CLI

**Files:**
- Create: `server/produce_reference_story_v2.py`
- Create: `server/tests/test_reference_story_v2_cli.py`

- [ ] **Step 1: Write parser tests**

```python
def test_v2_cli_supports_plan_generate_review_assemble():
    parser = build_parser()
    assert parser.parse_args(["plan", "raw.mp4", "out"]).command == "plan"
    assert parser.parse_args(["generate", "out", "--approve-paid-ops", "5"]).approve_paid_ops == 5
    assert parser.parse_args(["assemble", "out"]).command == "assemble"
```

- [ ] **Step 2: Run and verify RED**

```powershell
python -m pytest server/tests/test_reference_story_v2_cli.py -q
```

- [ ] **Step 3: Implement commands**

The CLI routes:

- `plan` -> `build_reference_story_v2_blueprint`
- `generate` -> `generate_flow_candidates`
- `accept` -> `review_flow_candidate`
- `assemble` -> `assemble_reference_story_v2`
- `remaster` -> `remaster_reference_story_v2`

- [ ] **Step 4: Run and verify GREEN**

```powershell
python -m pytest server/tests/test_reference_story_v2_cli.py -q
```

### Task 4: Generate and review Flow candidates

**Files:**
- Runtime artifacts under:
  `storage/deliverables/0809-production-v2-visual-upgrade/flow-candidates/`

- [ ] **Step 1: Verify the authenticated profile**

```powershell
& 'C:\Users\HPUSER\Documents\ChatGPT\New project\.venv\Scripts\gflow.exe' `
  auth status --profile sahilsharmabybit2
```

Expected: profile configured with cookies present.

- [ ] **Step 2: Plan V2**

```powershell
$env:PYTHONPATH='server'
python server\produce_reference_story_v2.py plan `
  'D:\Downloads\0809.mp4' `
  'storage\deliverables\0809-production-v2-visual-upgrade'
```

- [ ] **Step 3: Submit three sequential generations**

```powershell
python server\produce_reference_story_v2.py generate `
  'storage\deliverables\0809-production-v2-visual-upgrade' `
  --approve-paid-ops 5
```

Do not run generations in parallel and do not resubmit any attempt with a known
media ID.

- [ ] **Step 4: Inspect every candidate**

Review:

- all eight contact-sheet frames,
- full playback,
- generated-text OCR report,
- black/frozen/internal-cut gates,
- center-safe framing.

Reject a candidate if any hard gate fails.

- [ ] **Step 5: Accept windows**

Call `accept` with a 700-2200 ms window and six scores. Minimum total is 24/30
and every category must be at least three.

### Task 5: Assemble and master V2

**Files:**
- Modify: `server/app/editor/reference_story_v2.py`
- Modify: `server/tests/test_reference_story_v2.py`

- [ ] **Step 1: Write assembly tests**

```python
def test_v2_layers_apply_flow_labels_and_never_loop():
    layers = build_0809_v2_layers()
    flow = [layer for layer in layers if layer.flow_shot_id]
    assert len(flow) == 3
    assert all(layer.muted and layer.illustrative_label for layer in flow)


def test_v2_review_requires_stronger_visual_metrics():
    report = evaluate_reference_story_v2(
        frame_audit={
            "rendered_cut_count": 26,
            "median_shot_ms": 1900,
            "motion_score": 4.6,
            "dark_frame_ratio": 0.25,
            "mean_luminance": 82,
            "mean_saturation": 76,
        },
        coverage={
            "real_direct_source_ratio": 0.58,
            "flow_ratio": 0.11,
            "deterministic_graphic_ratio": 0.22,
            "direct_evidence_ratio": 0.17,
        },
        audio={
            "delay_passed": True,
            "duration_passed": True,
            "spectral_passed": True,
        },
        loudness={
            "integrated_lufs": -14.2,
            "true_peak_dbtp": -1.3,
        },
        narration={
            "token_retention": 1,
            "protected_tokens_missing": [],
        },
        metadata={
            "duration_seconds": 50.833,
            "frame_count": 1525,
            "width": 1080,
            "height": 1920,
            "fps": 30,
        },
    )
    assert report["automated_pass"] is True
```

- [ ] **Step 2: Run and verify RED**

```powershell
python -m pytest server/tests/test_reference_story_v2.py -q
```

- [ ] **Step 3: Implement assembly**

`assemble_reference_story_v2()` must:

1. Compile accepted Flow clips through `compile_production_plan()`.
2. Render the V2 explicit-layer composition.
3. Master with `master_reference_story_render()`.
4. Run V2 frame, coverage, evidence, audio, loudness, and fixed-language ASR
   review.
5. Advance only to `awaiting-final-approval` when all checks pass.

- [ ] **Step 4: Run and verify GREEN**

```powershell
python -m pytest server/tests/test_reference_story_v2.py -q
```

### Task 6: Render and perform production review

**Files:**
- Runtime outputs under:
  `storage/deliverables/0809-production-v2-visual-upgrade/`

- [ ] **Step 1: Assemble**

```powershell
python server\produce_reference_story_v2.py assemble `
  'storage\deliverables\0809-production-v2-visual-upgrade'
```

- [ ] **Step 2: Verify automated report**

Required measured results:

- zero failed checks,
- 24-30 cuts,
- median shot 1.5-2.4 seconds,
- motion 4.0-6.5,
- real/direct coverage at least 55%,
- Flow 8-14%,
- deterministic graphics at most 25%,
- evidence 15-20%,
- audio delay at most 20 ms,
- content retention at least 99%,
- true peak at or below -1 dBTP.

- [ ] **Step 3: Compare rendered pixels**

Inspect the hook, software update, evidence, server failure, brand-controls,
risk-containment, and ending rows against the supplied reference.

- [ ] **Step 4: Run all affected tests**

```powershell
$env:PYTHONPATH='server'
python -m pytest `
  server/tests/test_reference_story.py `
  server/tests/test_reference_story_v2.py `
  server/tests/test_reference_story_v2_cli.py `
  server/tests/test_production_v4.py `
  server/tests/test_flow_adapter.py `
  server/tests/test_flow_candidate.py `
  server/tests/test_production_assembly.py `
  -q
```

Expected: zero failures.

- [ ] **Step 5: Leave final approval unset**

The successful terminal state is `awaiting-final-approval` with:

```json
{
  "automated_pass": true,
  "human_approved": false
}
```
