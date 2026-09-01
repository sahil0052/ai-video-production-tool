import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";

import {
  compositionIdForPlan,
  findAvailableRendererPort,
} from "./render-args.mjs";

const rendererRoot = path.dirname(fileURLToPath(import.meta.url));
const values = new Map();
for (let index = 2; index < process.argv.length; index += 2) {
  values.set(process.argv[index], process.argv[index + 1]);
}

const planPath = path.resolve(values.get("--plan"));
const publicDir = path.resolve(values.get("--public-dir"));
const output = path.resolve(values.get("--output"));
const start = Number(values.get("--start"));
const end = Number(values.get("--end"));
const concurrency = Number(values.get("--concurrency") ?? 2);
if (
  !Number.isInteger(start) ||
  !Number.isInteger(end) ||
  start < 0 ||
  end < start
) {
  throw new Error("--start and --end must be a valid frame range");
}
if (!Number.isInteger(concurrency) || concurrency < 1) {
  throw new Error("--concurrency must be a positive integer");
}

const rawPlan = JSON.parse(await fs.readFile(planPath, "utf8"));
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
    pixelFormat: "yuv420p",
    outputLocation: output,
    inputProps,
    port: rendererPort,
    overwrite: true,
    concurrency,
    frameRange: [start, end],
  });
} finally {
  await fs.rm(bundleLocation, { recursive: true, force: true });
}
