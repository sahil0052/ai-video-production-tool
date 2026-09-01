# 0813 Live-Footage Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace every rejected slide, webpage, evidence-card, and dashboard visual in the 0813 edit with licensed live moving footage and minimal verified overlays.

**Architecture:** Keep the existing 38-shot timeline, captions, narration master, music, and sound design. Change the visual layer map so the rejected shots resolve to reviewed live-video assets; generate only transparent lower-third fact overlays, never full-frame graphics. Recompile the blueprint, render, and enforce both existing technical gates and a new “no rejected full-screen visual” gate.

**Tech Stack:** Python, Pillow, FFmpeg, OpenCV, Pexels API, existing production contracts and review pipeline.

---

### Task 1: Add regression coverage for the live-footage policy

**Files:**
- Modify: `server/tests/test_0813_training_parity.py`
- Modify: `server/build_0813_training_parity.py`

- [ ] **Step 1: Write failing tests for live-video shot mapping**

Add assertions that shots `4, 5, 10–16, 19, 20, 23–25, 27, 29, 32–37`
use video assets and never reference `evidence-*` or full-screen
`graphic-*` assets.

- [ ] **Step 2: Write a failing test for minimal overlays**

Assert that every replacement overlay is a transparent PNG, occupies less
than 28% of the frame, contains no fabricated number, and maps each exact
number to an evidence identifier.

- [ ] **Step 3: Run the focused tests**

Run:

```powershell
$env:PYTHONPATH='server'
server\.venv\Scripts\python.exe -m pytest `
  server\tests\test_0813_training_parity.py -q
```

Expected: failures proving the current evidence and dashboard assets remain.

### Task 2: Source and review missing live footage

**Files:**
- Create: `storage/deliverables/0813-production-v3-live-footage/asset-candidates/live-search/candidates.json`
- Create: `storage/deliverables/0813-production-v3-live-footage/asset-candidates/live-search/contact-sheet.jpg`
- Modify: `server/build_0813_training_parity.py`

- [ ] **Step 1: Query Pexels securely**

Read `PEXELS_API_KEY` from `.env` without logging it. Search portrait video
for:

- supermarket checkout scanning groceries;
- receipt and price-tag close-up;
- inflation shopping prices;
- trader reacting to market chart;
- apartment rent or housing cost.

- [ ] **Step 2: Download review candidates**

Keep the highest practical portrait MP4 for each candidate and write provider,
creator, source URL, license URL, remote ID, dimensions, duration, and local
path to `candidates.json`.

- [ ] **Step 3: Build and inspect contact sheets**

Extract four evenly spaced frames per candidate. Reject watermarks, generated
text, static footage, weak portrait framing, irrelevant products, and clips
without a visible action.

- [ ] **Step 4: Add selected assets and provenance**

Add only accepted clips to `REMOTE_ASSETS` and `asset-manifest.json`, including
SHA-256 checksums.

### Task 3: Replace full-screen cards with live footage

**Files:**
- Modify: `server/build_0813_training_parity.py`
- Modify: `server/render_0813_training_parity.py`

- [ ] **Step 1: Define the live source map**

Implement a single mapping for:

```python
LIVE_SHOT_ASSETS = {
    4: "licensed-grocery-market",
    5: "licensed-shopping-cart",
    10: "licensed-checkout-scan",
    11: "licensed-receipt-closeup",
    12: "licensed-grocery-produce",
    13: "licensed-price-tag-closeup",
    15: "licensed-market-tablet",
    16: "licensed-finance-workspace",
    19: "licensed-gas-station-wide",
    20: "licensed-gasoline-action",
    23: "licensed-apartment-facade",
    24: "licensed-trader-monitor",
    25: "licensed-market-tablet",
    27: "licensed-finance-workspace",
    29: "licensed-trader-monitor",
    32: "licensed-market-tablet",
    33: "licensed-trader-monitor",
    34: "presenter-edl",
    35: "licensed-finance-workspace",
    36: "licensed-market-tablet",
    37: "presenter-edl",
}
```

Use alternate source offsets and crop scales when an asset repeats.

- [ ] **Step 2: Update blueprint layers**

Assign `licensed-context`, `presenter`, or `direct-evidence-context` roles to
the replacement shots. Remove full-frame evidence and deterministic-graphic
layers from those shots.

- [ ] **Step 3: Update FFmpeg rendering**

Render every replacement as moving video with deliberate source trim, portrait
crop, conservative grade, and no looping. Preserve the existing hard-cut
boundaries.

- [ ] **Step 4: Run focused tests**

Run the test command from Task 1. Expected: all live-source mapping tests pass.

### Task 4: Add restrained verified fact overlays

**Files:**
- Modify: `server/build_0813_training_parity.py`
- Modify: `server/render_0813_training_parity.py`
- Test: `server/tests/test_0813_training_parity.py`

- [ ] **Step 1: Generate transparent overlay assets**

Create compact overlays for:

- `CPI = HOUSEHOLD BASKET`;
- `0.1% MONTHLY`;
- `3.4% YEARLY`;
- `ACTUAL = FORECAST`;
- `ENERGY −1.5%`;
- `GASOLINE −2.9%`;
- `SHELTER ≈ TWO-THIRDS`;
- `DOLLAR GAINED`;
- `RATE EXPECTATIONS SHIFTED`;
- `SPREAD LIMIT`, `PAUSE`, and `CONFIRMATION`.

Use no panels larger than the text’s fitted background and keep each overlay
below 28% frame area.

- [ ] **Step 2: Attach evidence identifiers**

Map each numerical overlay to the corresponding existing `EvidenceItem`.
Qualitative labels must not imply an unsupported result.

- [ ] **Step 3: Position overlays**

Use face/product collision-safe anchors and keep the existing compact captions
visible. Never cover eyes, hands performing an action, receipt totals, or chart
movement.

- [ ] **Step 4: Validate overlay geometry**

Render stills and assert no overflow, wrap, or collision.

### Task 5: Rebuild into a preserved V3 deliverable

**Files:**
- Create: `storage/deliverables/0813-production-v3-live-footage/`
- Preserve: `storage/deliverables/0813-production-v2-training-parity/`

- [ ] **Step 1: Point the scripts at V3**

Keep V2 unchanged and compile all new assets, manifests, layers, and review
artifacts into `0813-production-v3-live-footage`.

- [ ] **Step 2: Build and render**

Run:

```powershell
server\.venv\Scripts\python.exe server\build_0813_training_parity.py
server\.venv\Scripts\python.exe server\render_0813_training_parity.py
```

Expected: `edited.mp4` plus all production artifacts.

### Task 6: Verify visual and technical release readiness

**Files:**
- Create: `storage/deliverables/0813-production-v3-live-footage/review/live-replacement-contact-sheet.jpg`
- Modify: `storage/deliverables/0813-production-v3-live-footage/review-report.json`

- [ ] **Step 1: Run automated tests and full decode**

Run:

```powershell
$env:PYTHONPATH='server'
server\.venv\Scripts\python.exe -m pytest `
  server\tests\test_0813_training_parity.py `
  server\tests\test_production_assembly.py -q

ffmpeg -v error -i edited.mp4 -map 0:v:0 -map 0:a:0 -f null NUL
```

Expected: zero failures and zero decode errors.

- [ ] **Step 2: Verify the live-footage gate**

Require:

- zero rejected full-screen card/document treatments;
- at least 80% live moving footage across the replacement interval;
- no static replacement pair held longer than 500 ms;
- no unsupported number or factual label;
- no repeated source for more than two consecutive shots.

- [ ] **Step 3: Verify existing production gates**

Require 1080×1920 H.264/AAC, 100% narration retention, zero protected-term
loss, caption coverage and fitting, at least 80% cut/audio alignment,
101±5 BPM rendered-bed pulse, approximately −14.2 LUFS, and ≤−1 dBTP.

- [ ] **Step 4: Perform visual review**

Inspect the hook, CPI explanation, monthly/yearly proof, energy, shelter,
market-reaction, guardrail, and ending frames. Block release if any section
still resembles a slide deck or if the footage is semantically late.

> Workspace note: this folder is not a Git repository, so commit steps are not
> executable. Preserve V2 and keep V3 isolated to provide rollback.
