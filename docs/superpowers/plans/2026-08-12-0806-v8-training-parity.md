# 0806 V8 Training-Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a separate V8 edit whose frame composition, caption grammar, motion behavior and mixed-audio pulse match training reference #10 more closely than V7.

**Architecture:** Add reusable perceptual-parity measurements to the production audit, then add a versioned 0806 V8 blueprint module and builder. Reuse V7’s verified source captures and provenance, but recompose them with tighter crops, raw source evidence, restrained motion, a slower licensed music bed and Deepgram-aligned English caption windows.

**Tech Stack:** Python 3.11, Pydantic, OpenCV, NumPy, FFmpeg, Remotion/React, pytest.

---

### Task 1: Add perceptual-parity measurements

**Files:**
- Modify: `server/app/editor/production_audit.py`
- Modify: `server/app/editor/production_assembly.py`
- Test: `server/tests/test_production_audit.py`
- Test: `server/tests/test_production_assembly.py`

- [ ] **Step 1: Write failing tests for composition metrics**

Add fixtures containing clean dark negative space, bright blank space, detailed
UI and controlled static/moving frame pairs. Assert that a new
`measure_composition_parity(video)` report exposes:

```python
{
    "bright_uniform_blank_mean": float,
    "bright_uniform_blank_p90": float,
    "dark_uniform_blank_mean": float,
    "occupied_local_detail_mean": float,
    "edge_density_mean": float,
    "near_static_pair_ratio": float,
    "low_motion_pair_ratio": float,
}
```

- [ ] **Step 2: Run the focused tests and observe failure**

Run:

```powershell
python -m pytest tests/test_production_audit.py -k composition_parity -q
```

Expected: failure because `measure_composition_parity` does not exist.

- [ ] **Step 3: Implement the metric**

Decode at 10 FPS into 180×320 grayscale frames. Divide each frame into 200
local cells, classify bright/dark uniform cells from mean and standard
deviation, measure Canny edge density, and compare non-cut adjacent frames
after excluding differences at or above 25.

- [ ] **Step 4: Add V8-only release gates**

In `run_automated_production_review()`, identify V8 through
`story_profile == "automation-future-parity"` and add:

```python
0.060 <= edge_density_mean <= 0.090
0.25 <= near_static_pair_ratio <= 0.50
bright_uniform_blank_p90 <= 0.43
dark_uniform_blank_mean >= 0.28
```

Persist the report as `composition-parity.json`.

- [ ] **Step 5: Verify the focused tests**

Run:

```powershell
python -m pytest tests/test_production_audit.py tests/test_production_assembly.py -q
```

Expected: all tests pass.

### Task 2: Build strict caption timing and family parity

**Files:**
- Create: `server/app/editor/training_parity_0806.py`
- Test: `server/tests/test_training_parity_0806.py`

- [ ] **Step 1: Write failing caption tests**

Assert that:

```python
pages = build_v8_caption_pages(deepgram_words)
assert all(page.family == "technical-mono" for page in pages)
assert all(350 <= page.end_ms - page.start_ms <= 1300 for page in pages)
assert technical_mono_caption_share(pages) >= 0.96
assert caption_token_window_violations(pages) == []
assert 0.70 <= caption_coverage_ratio(pages, 41_400) <= 0.74
```

The `$110,000` spoken window must be covered by consecutive identical pages
whose individual holds stay within 1300 ms.

- [ ] **Step 2: Run the test and observe failure**

Run:

```powershell
python -m pytest tests/test_training_parity_0806.py -k caption -q
```

Expected: import failure because the V8 module does not exist.

- [ ] **Step 3: Implement the caption builder**

Define approved English phrases with Deepgram Nova-2 English-India time
windows. Use hard replacement, `center-74`, 480 px maximum width and exact
technical-mono family. Split long visible windows into consecutive identical
pages without visual interruption.

- [ ] **Step 4: Verify caption tests**

Run:

```powershell
python -m pytest tests/test_training_parity_0806.py -k caption -q
```

Expected: pass.

### Task 3: Build the V8 shot schedule and layers

**Files:**
- Modify: `server/app/editor/training_parity_0806.py`
- Test: `server/tests/test_training_parity_0806.py`

- [ ] **Step 1: Write failing visual-grammar tests**

Assert:

```python
layers = build_v8_layers()
coverage = estimate_role_coverage(layers)
assert 0.12 <= coverage["presenter"] <= 0.16
assert 0.34 <= coverage["real-product"] <= 0.42
assert 0.17 <= coverage["direct-evidence"] <= 0.21
assert coverage["flow-illustrative"] == 0
assert all(layer.source_role != "direct-evidence" or layer.border_radius == 0 for layer in layers)
assert all(abs(last.scale - first.scale) <= 0.025 for still-image layers)
```

Also assert that code, risk, attachment and tester layers use crop widths of
0.48 or less where required, and that the final shot is a tight presenter
frame rather than a split screen.

- [ ] **Step 2: Run and observe failure**

Run:

```powershell
python -m pytest tests/test_training_parity_0806.py -k "layers or schedule" -q
```

Expected: failure until V8 layers are implemented.

- [ ] **Step 3: Implement 21 role-specific shots**

Use the existing 41.4-second speech map, but:

- shorten the 9.42-second presenter reset to 10.70 seconds;
- use a dark code macro from 10.70-12.06 seconds;
- shorten the 27.78-second presenter lesson to 29.00 seconds;
- continue with a rule/risk graphic until 32.20 seconds;
- use a tight presenter CTA from 37.16-39.20 seconds;
- use a one-second product action bridge;
- end on a tight presenter from 40.20-41.40 seconds.

Remove white product backdrops, decorative context strips and continuous
translation/scale drift.

- [ ] **Step 4: Verify visual-grammar tests**

Run:

```powershell
python -m pytest tests/test_training_parity_0806.py -q
```

Expected: pass.

### Task 4: Prepare raw evidence frames and slower music

**Files:**
- Create: `server/build_0806_training_parity_v8.py`
- Test: `server/tests/test_training_parity_0806.py`

- [ ] **Step 1: Write failing asset-preparation tests**

Assert that V8:

- reads V7 source assets without mutating V7;
- creates evidence frames from the raw official captures
  `metatrader5-atc-history.png` and `mql5-atc-2008-risk-readable.png`;
- does not draw replacement document text;
- selects `feedback-dreams-588.mp3`;
- writes provider, creator, license, URL and checksum provenance.

- [ ] **Step 2: Implement evidence composition**

Create 1080×1920 frames with raw source pixels filling the usable frame:

- overview page on neutral dark surround;
- full-width championship excerpt;
- full-width MQL5 paragraph;
- source-pixel `$110,000` macro with only a deterministic underline and
  attribution outside the source crop.

- [ ] **Step 3: Implement music preparation**

Transcode the licensed candidate to 48 kHz WAV, trim one uninterrupted
41.4-second section, apply high-pass at 35 Hz, low-pass near 7000 Hz,
conservative EQ and short fades. Do not loop.

- [ ] **Step 4: Verify asset tests**

Run:

```powershell
python -m pytest tests/test_training_parity_0806.py -k "evidence or music" -q
```

Expected: pass.

### Task 5: Build, assemble and review V8

**Files:**
- Output: `storage/deliverables/0806-production-v8-training-parity/`

- [ ] **Step 1: Build the V8 blueprint**

Run:

```powershell
python server/build_0806_training_parity_v8.py
```

Expected: V8 artifacts are created without changing V7.

- [ ] **Step 2: Assemble the render**

Run the V4 production assembly against the V8 output. Keep all visual media
muted and mix the untouched dialogue master after visual rendering.

- [ ] **Step 3: Run full automated review**

Require every existing gate plus the V8 parity gates, technical-mono caption
share and zero token-window violations.

- [ ] **Step 4: Generate human comparison artifacts**

Create:

- `review/role-matched-comparison.jpg`;
- `review/reference-10-normalized-contact.jpg`;
- `review/v8-normalized-contact.jpg`;
- `review/caption-comparison.jpg`;
- `review/audio-comparison-metrics.json`.

- [ ] **Step 5: Inspect the complete video**

Review hook, code, evidence, risk, MT5 action and ending at full resolution.
Reject the candidate if any action is unreadable, any source page appears
redesigned, or any frame looks busier than its matched reference role.

### Task 6: Update the reusable editing skill

**Files:**
- Modify: `C:/Users/HPUSER/.codex/skills/edit-tech-story-videos/SKILL.md`
- Modify: `C:/Users/HPUSER/.codex/skills/edit-tech-story-videos/references/style-profile.md`
- Modify: `C:/Users/HPUSER/.codex/skills/edit-tech-story-videos/references/caption-system.md`
- Modify: `C:/Users/HPUSER/.codex/skills/edit-tech-story-videos/references/motion-audio-rules.md`

- [ ] **Step 1: Document perceptual parity gates**

Add the local-detail, static-pair, blank-space, caption-family and rendered
pulse checks. Explicitly state that global luminance, motion and source-role
coverage cannot prove reference parity.

- [ ] **Step 2: Document evidence and UI composition rules**

Require source pages to fill the usable frame and product actions to be
readable at phone size. Reject full-desktop UI even when authentic.

- [ ] **Step 3: Run skill tests and production tests**

Run:

```powershell
python -m pytest C:/Users/HPUSER/.codex/skills/edit-tech-story-videos/tests -q
python -m pytest server/tests/test_production_audit.py server/tests/test_production_assembly.py server/tests/test_training_parity_0806.py -q
```

Expected: all pass.

### Task 7: Final release-readiness audit

**Files:**
- Inspect: V8 `review-report.json`, `production-job.json`, media and comparison artifacts.

- [ ] **Step 1: Verify codec and artifact integrity**

Require 1080×1920 H.264/yuv420p, AAC 48 kHz, 30 FPS, no dead frames, no silent
tail and all required artifacts present.

- [ ] **Step 2: Verify objective-level parity**

Confirm each explicit design requirement with rendered-pixel or audio
evidence. Automated green checks are insufficient if role-matched frames still
look weaker.

- [ ] **Step 3: Set only automated approval**

Advance to `awaiting-final-approval` only when every automated and perceptual
gate passes. Keep `human_approved: false`.
