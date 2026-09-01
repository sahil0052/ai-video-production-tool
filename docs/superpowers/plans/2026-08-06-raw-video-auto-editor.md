# Raw Video Auto Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web application that accepts a vertical talking-head video under one minute and returns a cleaned, captioned, loudness-normalized H.264 edit.

**Architecture:** A React/Vite client uploads one video to a FastAPI server. The server persists job state on disk and runs a bounded Python media pipeline that analyzes the source with OpenCV and faster-whisper, cleans the transcript when configured, and renders with FFmpeg. The pipeline is intentionally conservative: it preserves the spoken timeline, normalizes audio, applies mild color and sharpness correction, standardizes portrait framing, and burns readable captions.

**Tech Stack:** React 19, Vite, TypeScript, FastAPI, Pydantic, pytest, OpenCV, faster-whisper, imageio-ffmpeg, FFmpeg.

---

## Project structure

```text
web/
  src/
    api.ts
    App.tsx
    components/
      UploadPanel.tsx
      ProcessingView.tsx
      ResultView.tsx
    styles.css
  package.json
  vite.config.ts
server/
  app/
    main.py
    config.py
    jobs.py
    models.py
    editor/
      analysis.py
      captions.py
      ffmpeg.py
      pipeline.py
  tests/
    test_analysis.py
    test_captions.py
    test_jobs.py
    test_api.py
  requirements.txt
storage/
  .gitkeep
```

### Task 1: Analysis contracts and source validation

**Files:**
- Create: `server/app/models.py`
- Create: `server/app/editor/analysis.py`
- Test: `server/tests/test_analysis.py`

- [x] Write failing tests proving vertical videos under 60 seconds are accepted, oversized or long videos are rejected, and hard-cut timestamps are returned in ascending order.
- [x] Run `python -m pytest server/tests/test_analysis.py -v` and verify failures are caused by missing implementation.
- [x] Implement `probe_video()`, `validate_source()` and `detect_hard_cuts()` with OpenCV and Pydantic models.
- [x] Re-run the test and keep the source duration limit at 65 seconds to tolerate container rounding.

### Task 2: Caption generation

**Files:**
- Create: `server/app/editor/captions.py`
- Test: `server/tests/test_captions.py`

- [x] Write failing tests for caption chunking, ASS timestamp formatting, escaping, line limits, and empty transcripts.
- [x] Run `python -m pytest server/tests/test_captions.py -v`.
- [x] Implement transcript segment normalization, phrase chunking and ASS subtitle generation.
- [x] Re-run the tests and preserve Unicode Hindi/Hinglish text.

### Task 3: FFmpeg command construction and render verification

**Files:**
- Create: `server/app/editor/ffmpeg.py`
- Create: `server/app/editor/pipeline.py`
- Test: `server/tests/test_pipeline.py`

- [x] Write failing tests for safe argument-list construction, H.264/AAC output settings, loudness normalization, subtitle inclusion and output validation.
- [x] Run `python -m pytest server/tests/test_pipeline.py -v`.
- [x] Implement FFmpeg discovery through `imageio_ffmpeg`, argument-list execution without a shell, bounded timeouts, progress callbacks and decode verification.
- [x] Implement a conservative pipeline: probe, transcribe, create captions, normalize audio, apply mild color correction, burn subtitles, encode H.264/AAC and verify.
- [x] Re-run pipeline tests.

### Task 4: Persistent jobs and API

**Files:**
- Create: `server/app/config.py`
- Create: `server/app/jobs.py`
- Create: `server/app/main.py`
- Test: `server/tests/test_jobs.py`
- Test: `server/tests/test_api.py`

- [x] Write failing tests for safe filenames, allowed media types, size limits, job persistence, unknown jobs and completed downloads.
- [x] Run `python -m pytest server/tests/test_jobs.py server/tests/test_api.py -v`.
- [x] Implement UUID job directories, atomic JSON status writes and a single bounded background worker.
- [x] Implement `POST /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/video`, `GET /api/health`.
- [x] Reject path traversal, unsupported extensions, files over 250 MB and more than one active upload per request.
- [x] Re-run API tests.

### Task 5: React interface

**Files:**
- Create: `web/package.json`
- Create: `web/vite.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/index.html`
- Create: `web/src/main.tsx`
- Create: `web/src/api.ts`
- Create: `web/src/App.tsx`
- Create: `web/src/components/UploadPanel.tsx`
- Create: `web/src/components/ProcessingView.tsx`
- Create: `web/src/components/ResultView.tsx`
- Create: `web/src/styles.css`

- [x] Build a dark, restrained editor UI with a compact header, central upload workspace and no marketing page.
- [x] Support drag-and-drop, validation feedback and upload progress.
- [x] Poll job state and show named stages rather than simulated percentages.
- [x] Show the final video in a real player with download and start-over actions.
- [x] Add keyboard focus, mobile behavior, reduced-motion behavior and clear error states.
- [x] Run `npm run build` in `web`.

### Task 6: End-to-end verification

**Files:**
- Create: `README.md`
- Create: `.gitignore`

- [x] Run all Python tests.
- [x] Run the frontend production build.
- [x] Start FastAPI and Vite.
- [x] Upload `D:\Downloads\0806.mp4`.
- [x] Verify the output is 1080×1920 H.264/AAC, under 65 seconds, decodable and approximately -14 LUFS.
- [x] Exercise upload, processing, playback, download, invalid-file and mobile flows in a browser.
- [x] Inspect console and network failures and capture the final UI screenshot.
- [x] Review all files for unsafe subprocess use, path traversal, unbounded uploads, debug artifacts and unrelated changes.
