# Deep Audit & Production Refinement Roadmap

## Important caveat before Part 1

I checked the repository directly rather than taking the QC summary on faith:

- `git log --all` shows PR #1 (`v0/motion-graphics-audit-improvements`) is still **open, unmerged**. `main` does not contain `render_master_v4.py`.
- `qc_report_v4.json` and `edited_v4.mp4` **do not exist anywhere in the repo, local or remote** (`find . -iname 'qc_report_v4.json'` and `-iname 'edited_v4*'` both return nothing; `storage/deliverables/voxpipe_0901_profitbricks/` only contains the v1 artifacts I reviewed previously).

So the "5/5 gates passed" result was produced by running the script on your local machine (where the real source video, Flow clips, and logo exist) and was not committed or pushed anywhere I can read. Part 1 below is therefore a **static code audit** of the committed `render_master_v4.py` and `profitbricks_0901.json` — confirmed by reading the actual file contents in this repo — not a re-verification of your local QC numbers, which I have no way to inspect. If you want me to check the actual `qc_report_v4.json` output, commit it (or paste its contents) and I will audit it directly instead of estimating.

## PART 1 — Static audit of the committed v4 pipeline

### What the code actually does (verified by reading `server/render_master_v4.py`)

- `preflight()` validates source/clip/logo existence and shot-timeline integrity (no negative-duration shots, no overlaps, no `FULL_FLOW` shot missing a `clip`) before any frame is written — confirmed present at lines 160-220.
- `interrupt_progress()` is a cosine pulse `(1 - cos(2*pi*phase))/2` on `phase = (t mod interval) / interval` -- this is a **fixed-period visual pulse**, not a content-aware cut. It always fires on FULL_CHAR/FULL_FLOW shots longer than `--interrupt-interval`, regardless of what is actually happening in the shot (a word landing, a number appearing, a gesture). That is the mechanism that makes "max gap 3.03s" pass, but it is pacing theater, not editing.
- `wrap_to_safe_width()` measures real glyph widths via `draw.textlength()` and rebalances to <=2 lines -- a real improvement over hand-typed strings, but it still hard-caps at 2 lines and silently concatenates overflow (`lines[:-1]` + `lines[-1]`) rather than shrinking font size or increasing hold time, so a caption that needs 3 lines will collapse.
- There is **no Ken-Burns on presenter footage outside of the interrupt pulse** -- `FULL_CHAR` shots shorter than `interrupt_interval` render the raw frame with zero motion. "Ken-Burns scaling" in this pipeline is exclusively the interrupt-pulse crop-zoom (`apply_pattern_interrupt`, max scale 1.06), reused for both "pattern interrupt" and "Ken Burns" -- they are the same mechanism wearing two names.
- Captions are positioned at a **fixed `top_y` anchored to y=1780**, independent of caption line count beyond re-centering; there's no collision check against the `OUTRO_FLOW` card or `SPLIT_FLOW` divider, so a caption timed to overlap a shot-type change is not verified against the layout it lands on.

### Scorecard (code-level, not a video re-render)

| Pillar | Score | Basis |
|---|---:|---|
| Visual Pacing / Pattern Interrupts | 6/10 | Interrupt cadence is now enforced and measurable (real improvement over the v1 static holds), but it's a uniform mechanical pulse applied to every long shot alike, not a cut driven by the words being said or a visual beat. Reads as "breathing" motion, not editing rhythm. |
| Typography / Caption Wrapping | 7/10 | Measured-width wrapping is a real fix over hand-typed fixed strings. Still hard-capped at 2 lines with silent overflow concatenation and no safe-area collision check against outro/split layouts. |
| Ken-Burns / Motion on Footage | 5/10 | Only exists as the interrupt pulse; presenter shots under the interrupt threshold have zero motion, so pacing depends entirely on shot-cutting rather than continuous camera-style movement. |
| Audio | 8/10 | `loudnorm` with explicit I/LRA/TP flags is correct practice; can't independently verify your local -14.0/-1.0 reading without the actual `qc_report_v4.json`. |
| Engineering Rigor (preflight/config/QC) | 8/10 | Preflight-before-render, externalized JSON timeline, and a QC-report contract are genuinely production-grade patterns versus the original hardcoded script. |

**Overall (code-level): 6.8/10** -- real engineering progress, but the "pattern interrupt" is currently a metronome, not a director.

## PART 2 -- Synthesis against 12 reference ecosystems

| # | Repo | Core idea worth stealing | Where it beats `render_master_v4.py` |
|---|---|---|---|
| 1 | `iart-ai/motion-skills` | 51 skills across 15 packs (kinetic type, data-viz, TikTok, WebGL, Manim), each a `SKILL.md` + `references/` + a **deliver-and-verify loop**: freeze a frame, tile a contact sheet, probe the encoded MP4 | Agent self-verifies visual output against a checklist before calling it done -- our pipeline currently trusts the QC report's own gates without an independent visual frame check |
| 2 | `haidrrrry/claude-remotion-skill` | 10 non-negotiable motion rules: never linear interpolation (springs/bezier+clamp), stagger everything, exits faster than entrances, 5-layer stack (bg->assets->graphics->grade->grain/vignette), all timing derived from `fps` | Our PIL loop has none of this: no spring easing (interrupt is a raw cosine), no layer separation (compositing is ad hoc per-layout branch), no color grade/grain pass at all |
| 3 | `Vincentwei1021/video-shotcraft` | 152 shot recipe cards + 209 motion previews, each a named, parameterized camera/composition pattern | Our timeline has 4 layout enums (`FULL_CHAR/FULL_FLOW/SPLIT_FLOW/OUTRO_FLOW`); a recipe-card system would replace "one Ken-Burns pulse for everything" with dozens of named, swappable motion treatments |
| 4 | `greensock/gsap-skills` | Timeline/ScrollTrigger primitives, correct easing/stagger idioms across React/Vue/vanilla | The canonical source for the spring/easing curves our cosine pulse should be replaced with |
| 5 | `Anil-matcha/vox-ai-motion-graphics-generator` | Automated Screenwriter -> Collage Artist -> Animator -> Editor pipeline for Vox-style paper collage explainers specifically | This is literally the aesthetic we're already using (diorama/paper collage) -- its keyframe/animation contract is the closest architectural precedent to migrate toward, not a generic video tool |
| 6 | `freshtechbro/claudedesignskills` | 27 plugins covering Three.js/GSAP/R3F/Babylon with generator scripts (e.g. `component_generator.py`, `timeline_builder.py`) that scaffold boilerplate instead of hand-writing it | Pattern to copy: parameterized generator scripts per shot-type instead of one monolithic `render()` function with `if shot.layout ==` branches |
| 7 | `sakuraoxo-clio/sakura-animate-text` | Text animation effects as **portable JSON motion contracts** translatable to GSAP/WAAPI/CSS | Directly solves caption motion: define caption entrance/exit as a portable contract instead of the current static outlined-text draw with no animation at all |
| 8 | `Yusuke710/manim-skill` (+ 3b1b/manim lineage) | Precise, formula-driven animation for data/number reveals | Relevant if the "evidence" fix from the prior audit (showing sourced numbers/charts) is implemented -- Manim-style animated counters would beat a static overlay |
| 9 | `heygen-com/hyperframes` | HTML/CSS -> deterministic MP4 via headless Chrome + FFmpeg; treats a whole video as a seekable web composition with a component catalog (transitions, captions, charts, maps) | This is the strongest architectural alternative to raw PIL frame-by-frame drawing -- CSS layout/animation instead of manually computing pixel positions for every text card |
| 10 | `calesthio/OpenMontage` | **Agent-orchestrated, no runtime Python orchestrator** -- the coding agent reads YAML pipeline manifests and stage-director skills, calls a `ToolRegistry` of 100+ tools, checkpoints state between stages | Biggest structural idea: split "what to do" (skill/manifest, editable without touching Python) from "how to do it" (tool implementation) -- directly addresses why every video needs a bespoke Python script today |
| 11 | `0xsline/OpenChatCut` | Local-first multitrack timeline editor with AI-agent/MCP hooks | Reference for exposing the render pipeline as an editable timeline UI rather than only a CLI |
| 12 | `ishu86/after-effects-mcp` | 70+ MCP tools to drive real After Effects (compositions, keyframes, MOGRTs) from an agent | Escape hatch for shots that need genuine AE-quality effects (particles, advanced masks) beyond what PIL/OpenCV can do; MCP-driven AE is the ceiling, HyperFrames/Remotion is the practical middle ground |

### Recommended target architecture

Move off PIL-per-frame drawing entirely and adopt a **declarative composition + tool-registry hybrid**:

1. **Rendering engine: Remotion (React/TypeScript)** over raw HTML/Puppeteer (HyperFrames) or PIL. Remotion gives frame-accurate `useCurrentFrame()`, has first-class Ken-Burns/spring primitives (via `remotion` + manual `spring()`), and every "shot" becomes a React component instead of an `if shot.layout ==` branch.
2. **Motion primitives: GSAP-style springs**, following `claude-remotion-skill`'s 10 rules -- replace `interrupt_progress()`'s raw cosine with `spring({fps, config: {damping, mass}})` so interrupts feel directed, not metronomic.
3. **Orchestration: OpenMontage's manifest pattern** -- a YAML/JSON pipeline manifest per video (already halfway there with `profitbricks_0901.json`) drives stage order (transcribe -> align -> shot-plan -> render -> QC), with the coding agent (not a Python script) making the creative calls at each stage and a `ToolRegistry` of small, composable tools underneath.
4. **Shot library: video-shotcraft's recipe-card model** -- define a `shots/` directory of named, parameterized motion recipes (e.g. `presenter-punch-in`, `number-counter-reveal`, `split-compare`) instead of 4 hardcoded layout enums.
5. **Captions: sakura-animate-text's JSON motion contract** -- captions become `{enter, hold, exit}` animation contracts, not static outlined text.

### File-by-file changes to implement next

1. **`renderer/` (new)** -- scaffold a Remotion project (`npx create-video@latest`). Move `TARGET_W/TARGET_H`, the color tokens (`GOLD/WHITE/INK`), and the four layout types into `renderer/src/compositions/`.
2. **`renderer/src/shots/` (new)** -- one component per shot recipe (`FullCharacter.tsx`, `FullFlow.tsx`, `SplitFlow.tsx`, `OutroCard.tsx`), each accepting the same `Shot` shape already defined in `server/render_master_v4.py`'s dataclass so the JSON config format doesn't need to change.
3. **`renderer/src/motion/interrupt.ts` (new)** -- port `interrupt_progress()`/`apply_pattern_interrupt()` to `spring()`-based easing per rule #1 of `claude-remotion-skill`, keeping the same `--interrupt-interval` contract but driven by word beats from `word_timestamps.json` where alignment is trustworthy, falling back to the fixed cadence only where it isn't (see the ASR fix below).
4. **`renderer/src/captions/Caption.tsx` (new)** -- port `wrap_to_safe_width()` (keep the measured-width logic, it's good) but add entrance/exit animation and a 3rd-line fallback (shrink font by 10% before concatenating) instead of silent overflow concatenation.
5. **`server/render_master_v4.py`** -- keep as the **audio normalization + preflight + QC-report** stage (its actual strengths); replace only the PIL compositing loop (`render()`, lines ~339-520) with a call to `npx remotion render` against the same `profitbricks_0901.json`, then re-mux with the already-working `loudnorm` audio step.
6. **`server/render_configs/profitbricks_0901.json`** -- add an `entrance`/`exit` block per caption (start with `{type: "fade", duration: 0.25}`) and a `recipe` field per shot referencing the new shot-component name, so the config, not the Python script, decides motion style.
7. **`docs/qc_report_v4.schema.json` (new)** -- formalize the QC report contract so "5/5 gates passed" is machine-checkable in CI, not just printed to stdout.

### ASR/caption alignment fix for Hinglish audio

The prior audit found `word_timestamps.json` collapses/hallucinates from ~22-44s of this video (code-mixed Hindi/English). Concrete fix, in order of effort:

1. **Force a Hinglish-aware Whisper variant.** Base/medium Whisper's language-ID heavily biases toward monolingual Hindi or English and degrades on code-switched speech; retranscribe with `language="hi"` forced (not auto-detect) plus `--word_timestamps True`, or swap to a model fine-tuned for code-mixed South Asian speech (e.g. the `vasista22/whisper-hindi-large-v2` family) as a second opinion.
2. **Add a forced-alignment pass**, not just decode timestamps: run WhisperX (or `stable-ts`) with wav2vec2-based alignment on top of the Whisper transcript -- decode timestamps drift on code-switches, but a dedicated alignment model anchors words to audio independent of the language model's confidence.
3. **Segment-level confidence gating**: when a segment's average log-probability or the compression-ratio heuristic exceeds Whisper's own hallucination thresholds, mark that span `low_confidence: true` in `word_timestamps.json` rather than emitting the Whisper text as fact -- the fallback for those spans should be the human-edited `transcript_clean.json` already in this repo, which is evidently the input someone hand-typed the captions from anyway.
4. **Feed the gated output into the new caption motion contract** (`renderer/src/captions/Caption.tsx`) so only high-confidence spans get word-level highlight animation; low-confidence spans render as static two-line cards (today's behavior) until confidence is fixed at the source.
