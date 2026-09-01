import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";

import {
  compositionIdForPlan,
  findAvailableRendererPort,
  isProductionV2Plan,
  parseRenderArgs,
  renderMediaColorOptionsForPlan,
} from "./render-args.mjs";

const rendererRoot = path.dirname(fileURLToPath(import.meta.url));
const args = parseRenderArgs(process.argv.slice(2));
const planPath = path.resolve(args.plan);
const publicDir = path.resolve(args.publicDir);
const output = path.resolve(args.output);
const rawPlan = JSON.parse(await fs.readFile(planPath, "utf8"));
const isProductionV2 = isProductionV2Plan(rawPlan);
const productionConcurrency = Number.parseInt(
  process.env.CUTLINE_REMOTION_CONCURRENCY ??
    (isProductionV2 ? "1" : "2"),
  10,
);
const hasReference0806V3Scenes = rawPlan.scenes?.some((scene) =>
  scene.treatment?.startsWith("0806-v3-"),
);

if (
  !isProductionV2 &&
  (rawPlan?.version !== "1.0" ||
    rawPlan?.profile !== "tech-story-v1" ||
    !Array.isArray(rawPlan?.timeline) ||
    rawPlan.timeline.length === 0)
) {
  throw new Error("The renderer received an unsupported edit plan payload");
}
if (
  !isProductionV2 &&
  path.basename(rawPlan.source_url) !== rawPlan.source_url
) {
  throw new Error("source_url must reference a file in the public directory");
}

await fs.mkdir(path.dirname(output), { recursive: true });
const rendererPort = await findAvailableRendererPort();

const bundleLocation = await bundle({
  entryPoint: path.join(rendererRoot, "src", "index.ts"),
  publicDir,
  enableCaching: true,
  webpackOverride: (configuration) => configuration,
});

try {
  const inputProps = { plan: rawPlan };
  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: compositionIdForPlan(rawPlan),
    inputProps,
    port: rendererPort,
  });

  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: "h264",
    crf: 18,
    ...renderMediaColorOptionsForPlan(rawPlan),
    audioBitrate: "192k",
    x264Preset: "medium",
    outputLocation: output,
    inputProps,
    port: rendererPort,
    overwrite: true,
    concurrency: hasReference0806V3Scenes
      ? 1
      : Math.max(1, productionConcurrency),
    onProgress: ({ progress }) => {
      process.stdout.write(
        `${JSON.stringify({ stage: "rendering", progress })}\n`,
      );
    },
  });
} finally {
  await fs.rm(bundleLocation, { recursive: true, force: true });
}
