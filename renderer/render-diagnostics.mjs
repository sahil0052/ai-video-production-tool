import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";

import {
  compositionIdForPlan,
  findAvailableRendererPort,
} from "./render-args.mjs";

const rendererRoot = path.dirname(fileURLToPath(import.meta.url));

const readArg = (name) => {
  const index = process.argv.indexOf(name);
  if (index === -1 || index + 1 >= process.argv.length) {
    throw new Error(`Missing ${name}`);
  }
  return process.argv[index + 1];
};

const planPath = path.resolve(readArg("--plan"));
const publicDir = path.resolve(readArg("--public-dir"));
const outputDir = path.resolve(readArg("--output-dir"));
const frames = readArg("--frames")
  .split(",")
  .map((value) => Number.parseInt(value, 10))
  .filter((value) => Number.isInteger(value) && value >= 0);

if (frames.length === 0) {
  throw new Error("At least one diagnostic frame is required");
}

const rawPlan = JSON.parse(await fs.readFile(planPath, "utf8"));
await fs.mkdir(outputDir, { recursive: true });
const rendererPort = await findAvailableRendererPort();

const bundleLocation = await bundle({
  entryPoint: path.join(rendererRoot, "src", "index.ts"),
  publicDir,
  enableCaching: true,
});

try {
  const inputProps = { plan: rawPlan };
  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: compositionIdForPlan(rawPlan),
    inputProps,
    port: rendererPort,
  });
  const manifest = [];
  for (const frame of frames) {
    const filename = `diagnostic-${String(frame).padStart(4, "0")}.png`;
    await renderStill({
      composition,
      serveUrl: bundleLocation,
      output: path.join(outputDir, filename),
      imageFormat: "png",
      frame,
      inputProps,
      port: rendererPort,
      overwrite: true,
    });
    manifest.push({
      frame,
      time_seconds: frame / composition.fps,
      path: filename,
    });
  }
  await fs.writeFile(
    path.join(outputDir, "diagnostic-manifest.json"),
    `${JSON.stringify(manifest, null, 2)}\n`,
    "utf8",
  );
} finally {
  await fs.rm(bundleLocation, { recursive: true, force: true });
}
