# 0813 Training-Reference V8 Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild all three 0813 reels as bespoke training-reference edits with
reference-specific visuals, captions, sound, and raw-faithful stereo dialogue.

**Architecture:** Preserve V7 unchanged. Add a profile-aware V8 planning layer
that creates one explicit visual/audio plan per story, render the muted visual
layers with the production renderer, and master dialogue/music/SFX separately
with FFmpeg. Reuse the proven source-pixel, caption, and pixel-audit techniques
from `build_0813_training_parity.py`, but split the new implementation into
focused reusable modules instead of another 100,000-line story file.

**Tech Stack:** Python 3.12, Pydantic, Deepgram, Pexels/Pixabay APIs, OpenCV,
Pillow, FFmpeg, Remotion/React, pytest.

---

## Locked output and references

Preserve:

`storage/deliverables/0813-all-three-v7-semantic-visuals`

Create:

`storage/deliverables/0813-all-three-v8-training-reference`

| Story | Source | Primary | Secondary |
|---|---|---:|---:|
| PPI | `D:\Downloads\0813 (1).mp4` | #13 news/evidence | #10 technical restraint |
| Backtest | `D:\Downloads\0813 (2).mp4` | #10 technical explanation | #4 cinematic technical |
| Lot Size | `D:\Downloads\0813 (3).mp4` | #10 technical explanation | #5 product demonstration |

`Profit Bricks_Reel 05.mp4` controls brand/CTA polish and audio texture only.
It must not replace the training reference selected for the technical body.

## File map

Create:

- `server/app/editor/training_reference_profiles.py`
- `server/app/editor/dialogue_mastering.py`
- `server/app/editor/training_caption_planner.py`
- `server/build_0813_v8_common.py`
- `server/build_0813_ppi_v8.py`
- `server/build_0813_backtest_v8.py`
- `server/build_0813_lotsize_v8.py`
- `server/render_0813_v8.py`
- `server/review_0813_v8.py`
- `server/tests/test_0813_v8_profiles.py`
- `server/tests/test_0813_v8_dialogue.py`
- `server/tests/test_0813_v8_captions.py`
- `server/tests/test_0813_v8_blueprints.py`
- `server/tests/test_0813_v8_review.py`

Modify:

- `server/app/production_models.py`
- `server/app/editor/production_audit.py`
- `server/app/editor/production_assembly.py`
- `renderer/src/components/CaptionLayer.tsx`
- `renderer/src/productionSchema.ts`

The workspace is not currently a Git repository. Replace commit checkpoints
with `git diff` only if a repository is initialized before execution;
otherwise use the listed test and artifact checkpoints.

### Task 1: Add explicit per-story reference profiles

**Files:**

- Create: `server/app/editor/training_reference_profiles.py`
- Modify: `server/app/production_models.py`
- Modify: `renderer/src/productionSchema.ts`
- Test: `server/tests/test_0813_v8_profiles.py`

- [ ] **Step 1: Write failing profile tests**

```python
from app.editor.training_reference_profiles import profile_for_story


def test_ppi_uses_news_evidence_profile() -> None:
    profile = profile_for_story("ppi")
    assert profile.primary_reference == 13
    assert profile.secondary_reference == 10
    assert profile.presenter_ratio == (0.14, 0.20)
    assert profile.hard_cut_count == (31, 36)
    assert profile.median_shot_ms == (1_000, 1_500)


def test_backtest_and_lot_size_do_not_inherit_social_kinetic() -> None:
    backtest = profile_for_story("backtest")
    lot_size = profile_for_story("lot-size")
    assert backtest.primary_reference == 10
    assert lot_size.primary_reference == 10
    assert backtest.caption_mode == "technical-reference"
    assert lot_size.caption_mode == "technical-product"
    assert backtest.presenter_ratio[1] <= 0.20
    assert lot_size.presenter_ratio[1] <= 0.20
```

- [ ] **Step 2: Run the tests and verify the module is missing**

Run:

```powershell
cd server
.\.venv\Scripts\python.exe -m pytest tests\test_0813_v8_profiles.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Add the profile contract**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class TrainingReferenceProfile:
    story_id: str
    primary_reference: int
    secondary_reference: int
    caption_mode: str
    hard_cut_count: tuple[int, int]
    median_shot_ms: tuple[int, int]
    presenter_ratio: tuple[float, float]
    dark_ratio: tuple[float, float]
    luminance: tuple[float, float]
    luminance_p10: tuple[float, float]
    luminance_p90: tuple[float, float]
    saturation: tuple[float, float]
    caption_coverage: tuple[float, float]
    cut_audio_alignment_min: float
```

Populate these exact profiles:

```python
PROFILES = {
    "ppi": TrainingReferenceProfile(
        story_id="ppi",
        primary_reference=13,
        secondary_reference=10,
        caption_mode="news-evidence",
        hard_cut_count=(31, 36),
        median_shot_ms=(1_000, 1_500),
        presenter_ratio=(0.14, 0.20),
        dark_ratio=(0.24, 0.36),
        luminance=(78, 96),
        luminance_p10=(15, 35),
        luminance_p90=(210, 240),
        saturation=(58, 78),
        caption_coverage=(0.68, 0.75),
        cut_audio_alignment_min=0.85,
    ),
    "backtest": TrainingReferenceProfile(
        story_id="backtest",
        primary_reference=10,
        secondary_reference=4,
        caption_mode="technical-reference",
        hard_cut_count=(18, 22),
        median_shot_ms=(1_700, 2_300),
        presenter_ratio=(0.14, 0.20),
        dark_ratio=(0.38, 0.55),
        luminance=(68, 95),
        luminance_p10=(5, 18),
        luminance_p90=(215, 245),
        saturation=(45, 75),
        caption_coverage=(0.68, 0.75),
        cut_audio_alignment_min=0.88,
    ),
    "lot-size": TrainingReferenceProfile(
        story_id="lot-size",
        primary_reference=10,
        secondary_reference=5,
        caption_mode="technical-product",
        hard_cut_count=(20, 25),
        median_shot_ms=(1_500, 2_100),
        presenter_ratio=(0.14, 0.20),
        dark_ratio=(0.30, 0.45),
        luminance=(75, 100),
        luminance_p10=(8, 22),
        luminance_p90=(210, 242),
        saturation=(55, 90),
        caption_coverage=(0.68, 0.75),
        cut_audio_alignment_min=0.88,
    ),
}
```

Add `primary_reference`, `secondary_reference`, and
`reference_role` to the production plan schema on both Python and TypeScript
sides. Reject free-form values such as `training references`.

- [ ] **Step 4: Run the profile tests**

Expected: PASS.

### Task 2: Rebuild dialogue from the raw source without global acceleration

**Files:**

- Create: `server/app/editor/dialogue_mastering.py`
- Modify: `server/app/editor/production_assembly.py`
- Test: `server/tests/test_0813_v8_dialogue.py`

- [ ] **Step 1: Write failing dialogue tests**

```python
def test_speech_segments_remain_at_one_x() -> None:
    plan = build_dialogue_plan(
        source=Path(r"D:\Downloads\0813 (2).mp4"),
        words=[
            {"text": "Backtest", "start_ms": 0, "end_ms": 420},
            {"text": "simple", "start_ms": 650, "end_ms": 970},
            {"text": "language", "start_ms": 1_040, "end_ms": 1_420},
        ],
    )
    assert all(segment.playback_rate == 1.0 for segment in plan.segments)
    assert plan.output_duration_ms == 1_260


def test_processed_dialogue_is_the_mix_source() -> None:
    plan = build_audio_plan(
        [
            {
                "id": "dialogue-source-untouched",
                "kind": "audio",
                "path": "assets/audio/dialogue-source-untouched.wav",
            },
            {
                "id": "dialogue-processed",
                "kind": "audio",
                "path": "assets/audio/dialogue-processed.wav",
            },
        ]
    )
    assert plan.dialogue_asset_id == "dialogue-processed"
    assert plan.untouched_dialogue_asset_id == "dialogue-source-untouched"


def test_master_stays_stereo() -> None:
    command = build_stereo_master_command(
        ffmpeg=Path("ffmpeg.exe"),
        silent_video=Path("rendered-silent.mp4"),
        dialogue=Path("dialogue-processed.wav"),
        music=Path("music.wav"),
        output=Path("edited.mp4"),
        duration_ms=48_800,
    )
    assert command[command.index("-ac") + 1] == "2"
```

- [ ] **Step 2: Verify the tests fail against the current wiring**

Expected failures:

- V7 selects `dialogue-original`;
- Backtest and Lot Size use 1.06×;
- final output is mono.

- [ ] **Step 3: Implement three distinct dialogue assets**

Create:

- `dialogue-source-untouched.wav`: raw 48 kHz stereo extraction;
- `dialogue-edited.wav`: silence-compressed, speech at 1.00×;
- `dialogue-processed.wav`: gently processed version of `dialogue-edited.wav`.

Use this policy:

```python
DialoguePolicy(
    speech_playback_rate=1.0,
    collapse_gap_over_ms=120,
    replacement_gap_ms=(50, 80),
    edit_crossfade_ms=12,
    preserve_channels=2,
)
```

Do not pass `atempo` for speech. Use short equal-power crossfades at EDL joins.

- [ ] **Step 4: Implement a conservative voice chain**

Use FFmpeg filters equivalent to:

```text
highpass=f=72,
afftdn=nr=7:nf=-32:tn=1,
deesser=i=0.10:m=0.25:f=0.48,
acompressor=threshold=-20dB:ratio=2:attack=12:release=140:makeup=1.5
```

Do not limit the dialogue stem. Limit only the completed master. Render an
A/B file containing raw, edited, and processed ten-second excerpts.

- [ ] **Step 5: Add raw-source fidelity gates**

Require:

- no speech segment above 1.00×;
- encoded delay within ±20 ms of `dialogue-edited.wav`;
- envelope correlation at least 0.95;
- no missing protected word;
- raw-to-processed speech-band spectral distance at most 5 dB;
- processed crest factor at least 15 dB;
- stereo output.

- [ ] **Step 6: Run dialogue tests**

Expected: PASS.

### Task 3: Replace the universal caption template

**Files:**

- Create: `server/app/editor/training_caption_planner.py`
- Modify: `renderer/src/components/CaptionLayer.tsx`
- Test: `server/tests/test_0813_v8_captions.py`

- [ ] **Step 1: Write failing caption tests**

```python
def test_backtest_is_reference_10_mono() -> None:
    pages = plan_captions(
        "backtest",
        words=[
            {"text": "Backtest", "start_ms": 0, "end_ms": 420},
            {"text": "practice", "start_ms": 500, "end_ms": 840},
            {"text": "match", "start_ms": 850, "end_ms": 1_100},
            {"text": "hai", "start_ms": 1_120, "end_ms": 1_320},
        ],
        duration_ms=1_800,
    )
    visible = sum(page.end_ms - page.start_ms for page in pages)
    technical = sum(
        page.end_ms - page.start_ms
        for page in pages
        if page.family == "technical-mono"
    )
    assert technical / visible >= 0.96
    assert all(31 <= page.font_size <= 34 for page in pages)
    assert all(page.max_width <= 500 for page in pages)


def test_caption_coverage_is_not_continuous() -> None:
    pages = plan_captions(
        "ppi",
        words=[
            {"text": "Actual", "start_ms": 0, "end_ms": 320},
            {"text": "result", "start_ms": 340, "end_ms": 650},
            {"text": "zero", "start_ms": 720, "end_ms": 1_020},
        ],
        duration_ms=1_500,
    )
    coverage = covered_ms(pages) / duration_ms(pages)
    assert 0.68 <= coverage <= 0.75
```

- [ ] **Step 2: Implement role-based families**

Use:

- PPI data/system beats: `technical-mono`, 31–34 px.
- PPI evidence beats: `documentary-clean`, 32–38 px.
- Backtest: at least 96% `technical-mono`.
- Lot Size product actions: `outlined-demo`, 52–64 px.
- Lot Size explanation: `technical-mono`.
- Presenter CTA only: `compact-pill`, 34–40 px.

Group one to three words normally; permit four only for a bound phrase. Keep
350–1,300 ms holds and sentence boundaries.

- [ ] **Step 3: Remove automatic yellow token coloring**

In `CaptionLayer.tsx`, replace:

```tsx
color: token.highlighted ? "#D9FF45" : "white"
```

with:

```tsx
color:
  page.family === "display-emphasis" && token.highlighted
    ? page.accent_color ?? "#D9FF45"
    : "white"
```

Technical and documentary captions must remain white.

- [ ] **Step 4: Render caption fixtures**

Generate:

- `review/caption-fixture-technical.jpg`;
- `review/caption-fixture-documentary.jpg`;
- `review/caption-fixture-product.jpg`;
- one in-context still per family and story.

- [ ] **Step 5: Run caption tests and renderer typecheck**

```powershell
cd server
.\.venv\Scripts\python.exe -m pytest tests\test_0813_v8_captions.py -q
cd ..\renderer
npm run typecheck
```

Expected: PASS.

### Task 4: Add semantic asset selection and treatment diversity

**Files:**

- Create: `server/build_0813_v8_common.py`
- Modify: `server/app/editor/production_audit.py`
- Test: `server/tests/test_0813_v8_blueprints.py`

- [ ] **Step 1: Add source and treatment contracts**

```python
@dataclass(frozen=True)
class V8Shot:
    id: str
    start_ms: int
    end_ms: int
    narration_phrase: str
    source_role: str
    reference_role: str
    primary_subject: str
    action: str
    treatment: str
    asset_id: str
    caption_family: str
```

Every shot must name one subject and one action. Reject:

- `primary_subject=""`;
- `reference_role="training-reference-primary"`;
- full desktop UI longer than 800 ms;
- the same treatment on more than two consecutive shots;
- a static image for a narrated action;
- presenter coverage above the selected profile.

- [ ] **Step 2: Add API-backed candidate retrieval**

Read keys only from `.env`. For each licensed beat:

1. query Pexels and Pixabay;
2. download up to three portrait candidates;
3. create an eight-frame contact sheet;
4. score semantic relevance, portrait crop, subject clarity, motion,
   watermark/text contamination, and license;
5. accept only scores of at least 24/30 with no category below three.

Persist source URL, creator, license page, checksum, query, and accepted trim.

- [ ] **Step 3: Add treatment-diversity QC**

Require at least six distinct treatment classes per reel, such as:

- evidence overview;
- evidence excerpt;
- product macro;
- cursor/state change;
- designed flow;
- opposing-direction diagram;
- tactile footage;
- presenter reset;
- CTA.

Do not count a different asset checksum as a different treatment.

- [ ] **Step 4: Run blueprint contract tests**

Expected: PASS.

### Task 5: Build the PPI V8 blueprint

**Files:**

- Create: `server/build_0813_ppi_v8.py`
- Test: `server/tests/test_0813_v8_blueprints.py`

- [ ] **Step 1: Encode this speech-led timeline**

| Time | Treatment |
|---|---|
| 0.00–2.20 | Three fast real ingredient/supplier macros; no split-screen; serif hook only. |
| 2.20–5.10 | Supplier price action and upstream-price label on the exact phrase. |
| 5.10–8.70 | Designed producer → wholesale → retail flow; technical mono captions. |
| 8.70–12.60 | CPI versus PPI two-stage comparison using customer and factory source footage. |
| 12.60–14.90 | Clean presenter reset and release-date setup. |
| 14.90–15.55 | Official BLS page overview. |
| 15.55–18.80 | Readable BLS excerpt and forecast/actual tracked highlights. |
| 18.80–21.40 | Source-pixel `0.0%` proof macro with attribution. |
| 21.40–25.00 | Designed explanation that zero does not mean every component was flat. |
| 25.00–28.60 | Source-pixel goods `−0.7%` and services `+0.2%` excerpts. |
| 28.60–31.80 | Opposing-direction diagram derived from the verified values. |
| 31.80–35.20 | Genuine market-reaction source plus short trading-desk context. |
| 35.20–38.20 | Real MT5 spread-limit action with tight crop and cursor/state change. |
| 38.20–41.00 | Real confirmation setting plus one restrained code/rule graphic. |
| 41.00–43.80 | Robot reads number / market reads reason comparison. |
| 43.80–46.20 | Presenter CTA with compact caption and clean 0.5-second finish. |

- [ ] **Step 2: Enforce PPI allocation**

```python
assert 0.14 <= presenter_ratio <= 0.20
assert 0.20 <= evidence_ratio <= 0.27
assert 0.20 <= designed_explanation_ratio <= 0.32
assert 0.22 <= licensed_context_ratio <= 0.35
assert real_product_ratio >= 0.08
```

- [ ] **Step 3: Verify all visible numbers against `evidence.json`**

No forecast, actual, goods, services, date, or market-reaction statement may
render without a matching evidence item and source capture.

### Task 6: Build the Backtest V8 blueprint

**Files:**

- Create: `server/build_0813_backtest_v8.py`
- Test: `server/tests/test_0813_v8_blueprints.py`

- [ ] **Step 1: Encode this speech-led timeline**

| Time | Treatment |
|---|---|
| 0.00–2.80 | Real cricket nets → wicket action, hard-cut on the contrast. |
| 2.80–5.80 | Real MT5 Strategy Tester setup versus live-market chart context. |
| 5.80–8.80 | Short presenter question reset. |
| 8.80–12.20 | Practice-match analogy as a restrained #10-style diagram. |
| 12.20–15.80 | Historical data timeline and real tester data controls. |
| 15.80–20.20 | Three condition macros: perfect price, fixed spread, instant execution. |
| 20.20–24.80 | Real spread/tick action plus deterministic delay/slippage diagram. |
| 24.80–29.70 | Overfitting curve: historical fit versus unseen data, marked illustrative. |
| 29.70–32.60 | Brief student/answer-sheet tactile footage. |
| 32.60–36.80 | Real demo forward-test configuration; no result or profit claim. |
| 36.80–41.20 | Practice score ≠ guarantee diagram and presenter lesson reset. |
| 41.20–46.20 | Real tester/product close plus clean CTA. |

- [ ] **Step 2: Enforce Backtest allocation**

```python
assert 0.14 <= presenter_ratio <= 0.20
assert 0.25 <= real_product_ratio <= 0.35
assert 0.30 <= designed_explanation_ratio <= 0.42
assert 0.15 <= cinematic_context_ratio <= 0.25
assert technical_caption_share >= 0.96
```

- [ ] **Step 3: Reject fake results**

Strategy Tester may show setup controls, dates, modeling mode, and a cursor
action. Hide balances, account identifiers, result curves, profits, and
unverified performance.

### Task 7: Build the Lot Size V8 blueprint

**Files:**

- Create: `server/build_0813_lotsize_v8.py`
- Test: `server/tests/test_0813_v8_blueprints.py`

- [ ] **Step 1: Encode this speech-led timeline**

| Time | Treatment |
|---|---|
| 0.00–2.20 | Tight MT5 lot-input action and product hook. |
| 2.20–5.70 | One pizza versus many pizzas using moving footage and a deterministic count. |
| 5.70–8.80 | Same unit price / different total as a clean multiplication graphic. |
| 8.80–12.80 | Lot size = quantity with a real input-field macro. |
| 12.80–17.60 | Small versus large position using matched UI crops. |
| 17.60–22.40 | Same market move / different relative impact with normalized bars; no currency. |
| 22.40–26.60 | Profit and loss scale symmetrically with lot size. |
| 26.60–31.80 | Stop distance + lot size = actual risk diagram. |
| 31.80–36.50 | Real max-lot and fixed-risk settings plus exact code-rule highlight. |
| 36.50–39.70 | Wrong setting repeats: deterministic loop graphic and code macro. |
| 39.70–43.20 | Entry = where; lot = size; risk = consequence. |
| 43.20–48.80 | Real EA/product close, short presenter CTA, clean finish. |

- [ ] **Step 2: Enforce Lot Size allocation**

```python
assert 0.14 <= presenter_ratio <= 0.20
assert 0.30 <= real_product_ratio <= 0.40
assert 0.30 <= designed_explanation_ratio <= 0.40
assert 0.10 <= licensed_context_ratio <= 0.18
```

- [ ] **Step 3: Keep numerical graphics qualitative**

Do not show fabricated profit, loss, account value, or currency. Relative
bars may use `1×` and `N×` only when clearly labelled `ILLUSTRATIVE`.

### Task 8: Build distinct music and semantic sound plans

**Files:**

- Modify: `server/app/editor/production_assembly.py`
- Create: `server/render_0813_v8.py`
- Test: `server/tests/test_0813_v8_dialogue.py`

- [ ] **Step 1: Select one uninterrupted track per story**

- PPI: 96–104 BPM documentary/news pulse.
- Backtest: 88–96 BPM dark technical bed.
- Lot Size: 92–100 BPM clean technical/product bed.

Reject vocals, bright EDM leads, obvious four-on-the-floor dance tracks, and
tracks that mask 250 Hz–4 kHz speech.

- [ ] **Step 2: Create distinct cue sheets**

- PPI: 10–12 cues for hook, source page, forecast, actual, goods/services
  reversal, market reaction, two UI actions, lesson, CTA.
- Backtest: 8–10 cues for cricket contrast, tester open, three conditions,
  live-friction turn, overfitting, forward test, guarantee, CTA.
- Lot Size: 8–10 cues for lot input, pizza count, scale changes, risk equation,
  code rule, wrong-setting loop, CTA.

Do not reuse the same five SFX files across all three reels.

- [ ] **Step 3: Mix in stereo**

Keep dialogue centered but preserve stereo music and effects. Apply 5–6 dB
speech ducking. Keep SFX 12–18 dB below dialogue and outside −100/+120 ms
protected word onsets.

- [ ] **Step 4: Master with linear gain**

Targets:

- −14.2 ±0.3 LUFS;
- no higher than −1 dBTP;
- 2.0–3.0 LU LRA;
- 15–18 dB crest factor;
- stereo AAC 48 kHz, 256 kb/s.

Do not use a second aggressive compressor after the dialogue chain.

### Task 9: Render explicit layers and prohibit template fallbacks

**Files:**

- Create: `server/render_0813_v8.py`
- Modify: `renderer/src/components/CaptionLayer.tsx`
- Test: `server/tests/test_0813_v8_blueprints.py`

- [ ] **Step 1: Compile each blueprint to explicit layers**

Every layer must include:

```python
{
    "shot_id": "ppi-proof-03",
    "source_role": "direct-evidence",
    "reference_role": "reference-13-evidence-excerpt",
    "asset_id": "bls-july-ppi-excerpt",
    "source_start_ms": 0,
    "source_end_ms": 1200,
    "crop": {"x": 0.08, "y": 0.22, "width": 0.84, "height": 0.46},
    "transform_keyframes": [
        {"at_ms": 0, "x": 0, "y": 0, "scale": 1.0, "rotate_deg": 0},
        {"at_ms": 1200, "x": 0, "y": -10, "scale": 1.04, "rotate_deg": 0},
    ],
    "opacity_keyframes": [
        {"at_ms": 0, "value": 1.0},
        {"at_ms": 1200, "value": 1.0},
    ],
    "muted": True,
}
```

Reject treatment-name switches and all visual audio.

- [ ] **Step 2: Render visuals first**

Render silent 1080×1920, 30 FPS, H.264/yuv420p files. Then attach the mastered
stereo mix. Do not loop footage to fill a shot.

- [ ] **Step 3: Generate per-story review artifacts**

Create:

- `analysis-report.md`;
- `reference-profile.json`;
- `storyboard.json`;
- `evidence.json`;
- `caption-plan.json`;
- `dialogue-edl.json`;
- `sound-cue-sheet.json`;
- `asset-manifest.json`;
- `frame-audit.json`;
- `audio-continuity.json`;
- `role-comparison.jpg`;
- `edited.mp4`.

### Task 10: Replace permissive QC with rendered-reference gates

**Files:**

- Modify: `server/app/editor/production_audit.py`
- Create: `server/review_0813_v8.py`
- Test: `server/tests/test_0813_v8_review.py`

- [ ] **Step 1: Write failing review tests**

```python
def test_v7_profile_is_blocked_for_reference_10() -> None:
    report = evaluate_story(
        story_id="backtest",
        metrics={
            "presenter_ratio": 0.668,
            "caption_coverage": 0.988,
            "caption_families": ["modern-outline"],
            "treatment_classes": 4,
        },
    )
    assert report["automated_pass"] is False


def test_unique_files_do_not_substitute_for_treatment_diversity() -> None:
    report = evaluate_treatment_diversity(
        asset_ids=[f"asset-{index}" for index in range(8)],
        treatments=["generic-stock"] * 8,
    )
    assert report["passed"] is False
```

- [ ] **Step 2: Add profile-aware pixel gates**

Measure every final frame for:

- hard cuts and median shot;
- P10/P90 and mean luminance;
- dark/bright share;
- saturation;
- edge density;
- near-static pair ratio;
- internal motion distribution;
- presenter pixels;
- visible source-role distribution;
- treatment diversity.

- [ ] **Step 3: Add caption pixel gates**

Reject:

- coverage outside the profile;
- wrong family share;
- technical caption height outside 31–34 px;
- width above 500 px for technical mono;
- face/UI collision;
- source-page obstruction;
- yellow active-word highlighting on technical/documentary captions.

- [ ] **Step 4: Add raw voice gates**

Compare the final encoded mix with both:

- `dialogue-source-untouched.wav`;
- `dialogue-edited.wav`.

The first proves protected-word retention and spectral preservation; the
second proves timing. Do not compare only with an already accelerated stem.

- [ ] **Step 5: Run review tests**

Expected: PASS, with V7 fixtures explicitly blocked.

### Task 11: Produce, inspect, and release the three V8 reels

**Files:**

- Output:
  `storage/deliverables/0813-all-three-v8-training-reference`

- [ ] **Step 1: Build all plans and assets**

```powershell
cd server
.\.venv\Scripts\python.exe build_0813_ppi_v8.py
.\.venv\Scripts\python.exe build_0813_backtest_v8.py
.\.venv\Scripts\python.exe build_0813_lotsize_v8.py
```

- [ ] **Step 2: Run targeted tests**

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_0813_v8_profiles.py `
  tests\test_0813_v8_dialogue.py `
  tests\test_0813_v8_captions.py `
  tests\test_0813_v8_blueprints.py `
  tests\test_0813_v8_review.py -q
```

Expected: all pass.

- [ ] **Step 3: Render all three**

```powershell
.\.venv\Scripts\python.exe render_0813_v8.py --story ppi
.\.venv\Scripts\python.exe render_0813_v8.py --story backtest
.\.venv\Scripts\python.exe render_0813_v8.py --story lot-size
```

- [ ] **Step 4: Run complete review**

```powershell
.\.venv\Scripts\python.exe review_0813_v8.py `
  "C:\websites\ai video production tool\storage\deliverables\0813-all-three-v8-training-reference"
```

Expected state: `awaiting-final-approval`. Automation must not set
`human_approved: true`.

- [ ] **Step 5: Perform the human comparison**

Watch each complete reel:

- headphones;
- phone speaker;
- mono fold-down;
- phone-size visual playback.

Compare hook, first explanation, evidence/product proof, midpoint mechanism,
lesson, and ending against the locked primary reference.

- [ ] **Step 6: Release only after every gate passes**

Final files:

- `0813-ppi.mp4`;
- `0813-backtest.mp4`;
- `0813-lot-size.mp4`.

## Final acceptance

- No global speech acceleration.
- Every spoken word remains audible and ordered.
- Processed dialogue is actually used.
- Stereo final audio.
- 15–18 dB crest factor and −14.2 ±0.3 LUFS.
- Presenter coverage within each story profile.
- Caption coverage 68–75%, with correct family geometry.
- No generic stock for a product action or factual proof.
- No fake UI, result, balance, profit, document, or number.
- At least six treatment classes per reel.
- Every artifact begins on the phrase it explains.
- Every source page is readable at phone size.
- Rendered pixels pass story-specific reference metrics.
- Human approval remains mandatory.
