import { Audio } from "@remotion/media";
import { Sequence, staticFile, useVideoConfig } from "remotion";

import type { EditPlan } from "../schema";
import { millisecondsToFrames } from "../timing";

export type AudioLayerPlan = {
  assets: EditPlan["assets"];
  audio: EditPlan["audio"];
};

export const findAudioAsset = (
  assets: AudioLayerPlan["assets"],
  assetId: string | null,
) =>
  assetId
    ? assets.find(
        (asset) => asset.id === assetId && asset.kind === "audio",
      )
    : undefined;

export const musicVolumeAtFrame = (
  frame: number,
  durationInFrames: number,
  fps = 30,
  baseGainDb?: number,
  automation: AudioLayerPlan["audio"]["music_gain_automation"] = [],
) => {
  const resolvedBaseGainDb =
    baseGainDb ?? 20 * Math.log10(0.12);
  const timeMs = (frame / fps) * 1000;
  const automatedGainDb = automation
    .filter(
      (window) =>
        window.start_ms <= timeMs && window.end_ms > timeMs,
    )
    .reduce((total, window) => total + window.gain_db, 0);
  const baseVolume =
    10 ** ((resolvedBaseGainDb + automatedGainDb) / 20);
  const fadeInFrames = Math.max(
    1,
    Math.min(30, Math.floor(durationInFrames / 2)),
  );
  const fadeIn = Math.min(1, Math.max(0, frame / fadeInFrames));
  return baseVolume * fadeIn;
};

export const AudioLayer: React.FC<{ plan: AudioLayerPlan }> = ({
  plan,
}) => {
  const { fps, durationInFrames } = useVideoConfig();
  const dialogue = findAudioAsset(
    plan.assets,
    plan.audio.dialogue_asset_id,
  );
  const music = findAudioAsset(plan.assets, plan.audio.music_asset_id);
  return (
    <>
      {dialogue ? (
        <Sequence
          from={millisecondsToFrames(
            plan.audio.dialogue_offset_ms,
            fps,
          )}
          premountFor={fps}
        >
          <Audio src={staticFile(dialogue.path)} volume={1} />
        </Sequence>
      ) : null}
      {music ? (
        <Audio
          src={staticFile(music.path)}
          volume={(frame) =>
            musicVolumeAtFrame(
              frame,
              durationInFrames,
              fps,
              plan.audio.music_base_gain_db,
              plan.audio.music_gain_automation,
            )
          }
        />
      ) : null}
      {plan.audio.sfx_cues.map((cue) => {
        const asset = findAudioAsset(plan.assets, cue.asset_id);
        if (!asset) {
          return null;
        }
        return (
          <Sequence
            key={cue.id}
            from={millisecondsToFrames(cue.start_ms, fps)}
            durationInFrames={millisecondsToFrames(
              cue.duration_ms,
              fps,
            )}
            premountFor={fps}
          >
            <Audio
              src={staticFile(asset.path)}
              trimBefore={millisecondsToFrames(
                cue.source_start_ms,
                fps,
              )}
              volume={() =>
                Math.min(cue.volume, 10 ** (cue.gain_db / 20))
              }
            />
          </Sequence>
        );
      })}
    </>
  );
};
