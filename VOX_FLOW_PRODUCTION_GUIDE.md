# 🎬 Vox & Google Flow Production Video Engine Guide

## 🚨 MANDATORY PRODUCTION RULES (STRICT ENFORCEMENT)

### 1. Presenter Framing (Snug Headroom & Zero Forehead Clipping)
- The presenter in the bottom split-screen (`1080x960`) must be framed snuggly (`crop=1080:960:0:320` or calibrated to hair top).
- **Hair Position**: Position the hair directly below the divider line with minimal empty wall space (~20–30px breathing room).
- **Face Visibility**: Full head, eyes, nose, mouth, and shoulders must be fully visible with zero forehead clipping.

---

### 2. Top Visual Framing (Edge-to-Edge Full Screen)
- The top visual pane must be rendered in full screen edge-to-edge cover (`1080x960`).
- **No Side Bars**: Never use side bars, pillarboxes, or blur-padded side wings.
- **Graphic Clearance**: Ensure all focal elements, text badges, and action remain centered within the 1080x960 top frame.

---

### 3. Zero Visual Repetition & No Looped Animations
- **1-to-1 Beat Mapping**: Every narrative beat (5–8s each) MUST have its own dedicated, unique 3D Google Flow video.
- **No Looping**: Never loop a 5–8s clip inside a longer beat with `-stream_loop -1`. For a 50–60s video, generate 7–8 unique Google Flow scenes so every section has distinct animation.
- **Semantic Topic Alignment**: Every visual must directly illustrate the exact concept spoken by the presenter (e.g., price surge, printing press, currency crash).

---

### 4. Captions & Typography (Selective Punchlines Only)
- **No Continuous Subtitles**: Do NOT display continuous subtitles for every minor spoken word.
- **Emphasis Punchlines Only**: Display only 5–6 high-impact punchline bursts on core emphasis moments (e.g., key statistics, turning points, call-to-actions).
- **Typography Sizing**: Extra-large bold uppercase styling (font size 76–80 in `Impact` / `Arial Black`) with bright yellow (`#FFE600`) or red (`#FF3333`) accent highlights.
- **Script Purity (Zero Urdu/Arabic Characters)**: Always transcribe/translate with clean English Latin alphabet (`task="translate"` in Whisper) to eliminate unwanted foreign script characters.

---

### 5. Timeline Duration Integrity (Zero Tail Cutoffs)
- **Container Duration Match**: Always extract the exact container duration via `ffprobe` (e.g. `57.61s`).
- **No Early Trimming**: Never truncate the video early based on speech silence. The entire presenter stream (including final reactions/pauses) must render to the last frame.

---

### 6. Broadcast Audio & Loudness Standard
- **EBU R128 Loudness**: Two-pass loudness normalization strictly targeting `-14.0 LUFS` ($\pm 0.5\text{ LUFS}$) with true peak below `-1.0 dBFS`.
- **Sample Rate**: `48,000 Hz` stereo AAC.
- **Zero Lip-Sync Drift**: Presenter dialogue stream `[0:v]` / `[0:a]` remains in an unbroken single-pass anchor.

---

### 7. Mandatory Pre-Delivery Visual QC Verification Layer
Before any video deliverable is handed over, the pipeline must execute an automated frame-by-frame visual audit:
- Extract and audit keyframes at 2.0s intervals across the complete timeline.
- Verify dimensions (`1080x1920`), container duration match, top/bottom pane contrast (no black frames), subtitle character purity, and EBU R128 loudness.
