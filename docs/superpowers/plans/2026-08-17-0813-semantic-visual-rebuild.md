# 0813 Semantic Visual Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild all three 0813 reels with presenter-led semantic allocation, unique supporting visuals, exact captions, and unchanged clean narration.

**Architecture:** Add shared semantic-allocation validation to the 0813 live-story pipeline, then replace each fixed V6 storyboard with a V7 speech-aligned storyboard. Keep the existing renderer, caption system, and audio path; strengthen review so repeated or semantically invalid visual schedules cannot pass.

**Tech Stack:** Python, pytest, FFmpeg, OpenCV, Pillow, Pexels/Pixabay licensed assets, existing 0813 renderer and review pipeline.

---

### Task 1: Encode the editorial contract in tests

**Files:**
- Modify: `server/tests/test_0813_ppi_live.py`
- Modify: `server/tests/test_0813_all_stories_live.py`

- [ ] Add assertions for V7 output folder names, 14–17 shots, 58–68%
  presenter pixels, and a 3.8-second presenter-free maximum.
- [ ] Add a three-story assertion that every non-presenter `asset_id` occurs
  exactly once across the complete set.
- [ ] Add role assertions requiring PPI `zero-not-uniform` and
  `opposite-directions` to use presenter footage.
- [ ] Add a regression assertion forbidding the Lot Size fireplace asset
  `pixabay-17177`.
- [ ] Run:

```powershell
cd server
& ".venv\Scripts\python.exe" -m pytest `
  tests/test_0813_ppi_live.py `
  tests/test_0813_all_stories_live.py -q
```

Expected: failures on V6 output names, shot counts, presenter allocation, and
asset repetition.

### Task 2: Add shared semantic and uniqueness validation

**Files:**
- Modify: `server/story_0813_live_common.py`
- Modify: `server/review_0813_ppi_live.py`

- [ ] Add `visual_job` to `shot()` and persist it in `storyboard.json`.
- [ ] Add `semantic_visual_failures(storyboard)` that rejects missing jobs,
  abstract full-frame B-roll, more than two consecutive non-presenter shots,
  and a presenter-free run over 3.8 seconds.
- [ ] Add `visual-uniqueness.json` containing asset counts, repeated IDs,
  repeated duration, and pass/fail.
- [ ] Add `semantic-visuals` and `visual-uniqueness` to `evaluate_release`.
- [ ] Run the targeted test suite and confirm the new validator tests pass
  while storyboard tests remain red.

### Task 3: Rebuild the PPI storyboard

**Files:**
- Modify: `server/build_0813_ppi_live.py`

- [ ] Change output to
  `0813-production-v7-semantic-visuals`.
- [ ] Use 16 speech-aligned shots:
  hook split, producer action, presenter definition, checkout, factory,
  presenter release setup, official evidence, presenter zero explanation,
  unique goods footage, unique services footage, presenter opposite-move
  explanation, unique market reaction, presenter controls, presenter lesson
  beats, and presenter CTA.
- [ ] Use every non-presenter asset once.
- [ ] Generate a phone-readable official BLS evidence video from genuine
  source pixels and retain capture provenance.
- [ ] Preserve V6 caption generation and audio planning unchanged.

### Task 4: Rebuild the Backtest storyboard

**Files:**
- Modify: `server/build_0813_backtest_live.py`

- [ ] Change output to
  `0813-production-v7-semantic-visuals-take-2`.
- [ ] Use 15–16 shots with unique cricket, Strategy Tester, code, trader,
  student, forward-test, and ending sources.
- [ ] Use presenter footage for definitions, assumptions, friction,
  overfitting, risk, lesson, and CTA.
- [ ] Remove repeated Strategy Tester and student-writing shots.
- [ ] Preserve exact captions and clean narration.

### Task 5: Rebuild the Lot Size storyboard

**Files:**
- Modify: `server/build_0813_lotsize_live.py`

- [ ] Change output to
  `0813-production-v7-semantic-visuals-take-3`.
- [ ] Replace the fireplace with real pizza-box quantity footage.
- [ ] Use each product/context asset once and keep product actions readable.
- [ ] Put the presenter on quantity, impact, profit/loss, stop distance,
  actual risk, wrong settings, lesson, and CTA.
- [ ] Preserve exact captions and clean narration.

### Task 6: Build, render, and review

**Files:**
- Generate: the three V7 deliverable directories

- [ ] Run all three builders.
- [ ] Run all three renderer invocations with
  `VIDEO_STORY_BUILD_MODULE`.
- [ ] Run all three review invocations.
- [ ] Require all release checks, including semantic allocation and visual
  uniqueness, to pass.
- [ ] Inspect every shot contact sheet and the PPI evidence frame at full
  resolution.
- [ ] Run the perceptual duplicate scan and reject non-adjacent duplicate
  source frames.

### Task 7: Package verified outputs

**Files:**
- Generate:
  `storage/deliverables/0813-all-three-v7-semantic-visuals`

- [ ] Copy the three reviewed `edited.mp4` files with descriptive names.
- [ ] Copy each review report, caption-accuracy report, semantic allocation
  report, and visual-uniqueness report.
- [ ] Verify package checksums match source deliverables.
- [ ] Run the complete 0813 test suite and Python compile checks.
