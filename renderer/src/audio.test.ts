import { readFileSync } from "node:fs";

import { describe, expect, test } from "vitest";

import { findAudioAsset, musicVolumeAtFrame } from "./components/AudioLayer";
import type { EditPlan } from "./schema";

const assets: EditPlan["assets"] = [
  {
    id: "music",
    kind: "audio",
    path: "assets/music.wav",
    keywords: ["music"],
    provenance: "generated-original",
    license: "Original",
    provider: null,
    remote_id: null,
    creator: null,
    source_url: null,
    license_url: null,
    search_query: null,
    start_ms: null,
    end_ms: null,
  },
];

describe("audio layer helpers", () => {
  test("resolves an audio asset by id", () => {
    expect(findAudioAsset(assets, "music")?.path).toBe("assets/music.wav");
    expect(findAudioAsset(assets, "missing")).toBeUndefined();
  });

  test("fades in and preserves the score's authored tail", () => {
    expect(musicVolumeAtFrame(0, 300)).toBe(0);
    expect(musicVolumeAtFrame(30, 300)).toBeCloseTo(0.12);
    expect(musicVolumeAtFrame(150, 300)).toBeCloseTo(0.12);
    expect(musicVolumeAtFrame(299, 300)).toBeCloseTo(0.12);
  });

  test("applies authored gain automation during dialogue", () => {
    const automation = [
      {
        start_ms: 1000,
        end_ms: 2000,
        gain_db: -6,
        reason: "dialogue duck",
      },
    ];

    const unducked = musicVolumeAtFrame(
      75,
      300,
      30,
      -18,
      automation,
    );
    const ducked = musicVolumeAtFrame(
      45,
      300,
      30,
      -18,
      automation,
    );

    expect(unducked).toBeCloseTo(10 ** (-18 / 20), 4);
    expect(ducked).toBeCloseTo(10 ** (-24 / 20), 4);
    expect(ducked).toBeLessThan(unducked);
  });

  test("plays the generated full-length score once without looping", () => {
    const source = readFileSync(
      new URL("./components/AudioLayer.tsx", import.meta.url),
      "utf8",
    );

    expect(source).not.toMatch(/\bloop(?:VolumeCurveBehavior)?\b/);
  });

  test("limits every sound effect sequence to its declared cue duration", () => {
    const source = readFileSync(
      new URL("./components/AudioLayer.tsx", import.meta.url),
      "utf8",
    );

    expect(source).toMatch(
      /durationInFrames=\{millisecondsToFrames\(\s*cue\.duration_ms,\s*fps,\s*\)\}/,
    );
    expect(source).toMatch(
      /trimBefore=\{millisecondsToFrames\(\s*cue\.source_start_ms,\s*fps,\s*\)\}/,
    );
  });
});
