import React from "react";
import {
  AbsoluteFill,
  Composition,
  Img,
  interpolate,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface DioramaSceneProps {
  imageSrc: string;
  cameraMotion?: "push_in" | "pan_left" | "pan_right" | "dive_down" | "float";
  durationInFrames: number;
}

const DioramaScene: React.FC<DioramaSceneProps> = ({
  imageSrc,
  cameraMotion = "push_in",
  durationInFrames,
}) => {
  const frame = useCurrentFrame();

  const progress = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Smooth quadratic easing
  const ease = progress * progress * (3 - 2 * progress);

  let scale = 1.0;
  let translateX = 0;
  let translateY = 0;

  if (cameraMotion === "push_in") {
    scale = 1.0 + 0.12 * ease;
  } else if (cameraMotion === "pan_left") {
    scale = 1.08;
    translateX = -35 * ease;
  } else if (cameraMotion === "pan_right") {
    scale = 1.08;
    translateX = 35 * ease;
  } else if (cameraMotion === "dive_down") {
    scale = 1.08;
    translateY = -30 * ease;
  } else {
    scale = 1.04 + 0.02 * Math.sin(frame * 0.06);
  }

  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: "#C9BB9C" }}>
      <div
        style={{
          width: "100%",
          height: "100%",
          transform: `scale(${scale}) translate(${translateX}px, ${translateY}px)`,
          transformOrigin: "center center",
        }}
      >
        <Img
          src={staticFile(imageSrc)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

export const Vox0826TopHalf: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#C9BB9C", width: 1080, height: 960, overflow: "hidden" }}>
      {/* SCENE 1: 0.00s - 2.96s (0 - 88f) | BRAIN PSYCHOLOGY */}
      <Sequence from={0} durationInFrames={88}>
        <DioramaScene imageSrc="vox_scenes/vox0826_01_brain.jpg" cameraMotion="push_in" durationInFrames={88} />
      </Sequence>

      {/* SCENE 2: 2.96s - 5.42s (88 - 162f) | ₹1,000 FEAR */}
      <Sequence from={88} durationInFrames={74}>
        <DioramaScene imageSrc="vox_scenes/vox0826_02_fear.jpg" cameraMotion="pan_left" durationInFrames={74} />
      </Sequence>

      {/* SCENE 3: 5.42s - 7.24s (162 - 217f) | ₹10,000 GREED JUMP */}
      <Sequence from={162} durationInFrames={55}>
        <DioramaScene imageSrc="vox_scenes/vox0826_03_greed.jpg" cameraMotion="dive_down" durationInFrames={55} />
      </Sequence>

      {/* SCENE 4: 7.24s - 10.50s (217 - 315f) | CONFIDENCE & EGO */}
      <Sequence from={217} durationInFrames={98}>
        <DioramaScene imageSrc="vox_scenes/vox0826_04_ego.jpg" cameraMotion="push_in" durationInFrames={98} />
      </Sequence>

      {/* SCENE 5: 10.50s - 13.50s (315 - 405f) | OVERCONFIDENCE TRAP */}
      <Sequence from={315} durationInFrames={90}>
        <DioramaScene imageSrc="vox_scenes/vox0826_04_ego.jpg" cameraMotion="pan_right" durationInFrames={90} />
      </Sequence>

      {/* SCENE 6: 13.50s - 16.50s (405 - 495f) | WIN STREAK */}
      <Sequence from={405} durationInFrames={90}>
        <DioramaScene imageSrc="vox_scenes/vox0826_05_size.jpg" cameraMotion="push_in" durationInFrames={90} />
      </Sequence>

      {/* SCENE 7: 16.50s - 19.50s (495 - 585f) | POSITION SIZE 10X */}
      <Sequence from={495} durationInFrames={90}>
        <DioramaScene imageSrc="vox_scenes/b08_leverage.jpg" cameraMotion="dive_down" durationInFrames={90} />
      </Sequence>

      {/* SCENE 8: 19.50s - 22.50s (585 - 675f) | DRAWDOWN CRASH */}
      <Sequence from={585} durationInFrames={90}>
        <DioramaScene imageSrc="vox_scenes/b09_fast_loss.jpg" cameraMotion="dive_down" durationInFrames={90} />
      </Sequence>

      {/* SCENE 9: 22.50s - 25.50s (675 - 765f) | REVENGE TRADING */}
      <Sequence from={675} durationInFrames={90}>
        <DioramaScene imageSrc="vox_scenes/b10_emotions_revenge.jpg" cameraMotion="pan_left" durationInFrames={90} />
      </Sequence>

      {/* SCENE 10: 25.50s - 28.50s (765 - 855f) | NOT THE MARKET */}
      <Sequence from={765} durationInFrames={90}>
        <DioramaScene imageSrc="vox_scenes/b04_not_market.jpg" cameraMotion="push_in" durationInFrames={90} />
      </Sequence>

      {/* SCENE 11: 28.50s - 31.00s (855 - 930f) | ACCOUNT DAMAGE */}
      <Sequence from={855} durationInFrames={75}>
        <DioramaScene imageSrc="vox_scenes/b05_mistakes.jpg" cameraMotion="dive_down" durationInFrames={75} />
      </Sequence>

      {/* SCENE 12: 31.00s - 33.80s (930 - 1014f) | DISCIPLINE & EA */}
      <Sequence from={930} durationInFrames={84}>
        <DioramaScene imageSrc="vox_scenes/b12_ea_bot.jpg" cameraMotion="pan_right" durationInFrames={84} />
      </Sequence>

      {/* SCENE 13: 33.80s - 36.46s (1014 - 1094f) | FOLLOW CTA */}
      <Sequence from={1014} durationInFrames={80}>
        <DioramaScene imageSrc="vox_scenes/b13_cta_follow.jpg" cameraMotion="push_in" durationInFrames={80} />
      </Sequence>
    </AbsoluteFill>
  );
};

export const Vox0826TopHalfComposition: React.FC = () => {
  return (
    <Composition
      id="Vox0826TopHalf"
      component={Vox0826TopHalf}
      durationInFrames={1094}
      fps={30}
      width={1080}
      height={960}
    />
  );
};
