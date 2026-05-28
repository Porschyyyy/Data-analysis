import type * as React from "react";
import { pipelineSteps } from "./constants";
import { callApi, chooseFolderRequest, readHeadersRequest } from "./pipelineApi";
import {
  alignmentPayload,
  calibrationPayload,
  cosmicPayload,
  getOutputPng,
  headersPayload,
  lightcurvePayload,
  photometryPayload,
  trimPayload,
} from "./pipelinePayloads";
import {
  addDoneStep,
  getRunSteps,
  parseStarPositions,
  requireOutputPath,
  requireRawPath,
} from "./pipelineUtils";
import type { AddLog, PlotStyle, StepKey, TabKey, PreviewMode } from "../types/pipeline";

type BaseActionContext = {
  rawPath: string;
  outputPath: string;
  xStar: string;
  yStar: string;
  positionsText: string;
  plotStyle: PlotStyle;
  graphTitle: string;
  usePreset: boolean;
  useCommonMinSize: boolean;
  addLog: AddLog;
  setActiveTab: (tab: TabKey) => void;
  setActiveStep: (step: string) => void;
  setDoneSteps: React.Dispatch<React.SetStateAction<string[]>>;
  setImagePath: (path: string) => void;
  setFitsPreviewPath: (path: string) => void;
  setPreviewMode: (mode: PreviewMode) => void;
  setPreviewVersion: React.Dispatch<React.SetStateAction<number>>;
  detectedGroups: { group_name: string; n_files: number; example_files: string[] }[];
  setDetectedGroups: React.Dispatch<
    React.SetStateAction<{ group_name: string; n_files: number; example_files: string[] }[]>
  >;
  frameRoleMap: Record<string, string>;
  setFrameRoleMap: React.Dispatch<React.SetStateAction<Record<string, string>>>;
};

export async function chooseFolder(
  target: "raw" | "output",
  ctx: Pick<BaseActionContext, "rawPath" | "outputPath" | "addLog" | "setImagePath"> & {
    setRawPath: (path: string) => void;
    setOutputPath: (path: string) => void;
    setFitsPreviewPath: (path: string) => void;
  }
) {
  try {
    const currentPath = target === "raw" ? ctx.rawPath : ctx.outputPath;
    const data = await chooseFolderRequest(target, currentPath, ctx.addLog);

    if (!data.path) {
      ctx.addLog("Folder selection cancelled.");
      return;
    }

    if (target === "raw") {
      ctx.setRawPath(data.path);
      ctx.addLog(`Raw folder selected: ${data.path}`);
    } else {
      ctx.setOutputPath(data.path);
      ctx.setImagePath(`${data.path}/photometry/lightcurve_academic.png`);
      ctx.setFitsPreviewPath("");
      ctx.addLog(`Output folder selected: ${data.path}`);
    }
  } catch (err) {
    ctx.addLog(err instanceof Error ? `ERROR: ${err.message}` : "ERROR: Unknown folder selection error");
  }
}

export async function plotOnly(ctx: BaseActionContext, writeDoneLog = true) {
  if (!requireOutputPath(ctx.outputPath, ctx.addLog, ctx.setActiveTab)) return;

  try {
    ctx.setActiveStep("lightcurve");
    const outputPng = getOutputPng(ctx.outputPath, ctx.plotStyle);

    await callApi(
      "/plot-lightcurve",
      lightcurvePayload({
        outputPath: ctx.outputPath,
        outputPng,
        plotStyle: ctx.plotStyle,
        graphTitle: ctx.graphTitle,
        usePreset: ctx.usePreset,
      }),
      ctx.addLog
    );

    ctx.setImagePath(outputPng);
    ctx.setPreviewMode("plot");
    ctx.setPreviewVersion((v) => v + 1);
    addDoneStep(ctx.setDoneSteps, "lightcurve");
    ctx.setActiveStep("");

    if (writeDoneLog) ctx.addLog("Plot only finished.");
  } catch (err) {
    ctx.setActiveStep("");
    ctx.addLog(err instanceof Error ? `ERROR: ${err.message}` : "ERROR: Unknown error");
  }
}

export async function runPipeline(ctx: BaseActionContext & { runUntil: StepKey }) {
  if (!requireRawPath(ctx.rawPath, ctx.addLog, ctx.setActiveTab)) return;
  if (!requireOutputPath(ctx.outputPath, ctx.addLog, ctx.setActiveTab)) return;

  const selectedSteps = getRunSteps(pipelineSteps, ctx.runUntil);
  const x = Number(ctx.xStar);
  const y = Number(ctx.yStar);

  if (selectedSteps.some((step) => step.key === "alignment") && (!Number.isFinite(x) || !Number.isFinite(y))) {
    ctx.addLog("ERROR: Please enter reference star x_star and y_star first.");
    ctx.setActiveTab("stars");
    return;
  }

  if (selectedSteps.some((step) => step.key === "photometry")) {
    const positions = parseStarPositions(ctx.positionsText, ctx.addLog);
    if (!positions) {
      ctx.setActiveTab("stars");
      return;
    }
  }

  ctx.setDoneSteps([]);

  try {
    for (const step of selectedSteps) {
      ctx.setActiveStep(step.key);

      if (step.key === "headers") await callApi("/read-headers", headersPayload(ctx.rawPath), ctx.addLog);
      if (step.key === "calibration") await callApi("/run-calibration", calibrationPayload(ctx.rawPath, ctx.outputPath), ctx.addLog);
      if (step.key === "trim") await callApi("/run-trim", trimPayload(ctx.outputPath, ctx.useCommonMinSize), ctx.addLog);
      if (step.key === "cosmic") await callApi("/run-cosmic-ray", cosmicPayload(ctx.outputPath), ctx.addLog);
      if (step.key === "alignment") await callApi("/run-alignment", alignmentPayload(ctx.outputPath, x, y), ctx.addLog);
      if (step.key === "photometry") {
        const positions = parseStarPositions(ctx.positionsText, ctx.addLog);
        if (!positions) throw new Error("Invalid star positions.");
        await callApi("/run-photometry", photometryPayload(ctx.outputPath, positions), ctx.addLog);
      }
      if (step.key === "lightcurve") await plotOnly(ctx, false);

      addDoneStep(ctx.setDoneSteps, step.key);
    }

    ctx.setActiveStep("");
    ctx.addLog("Pipeline finished.");
  } catch (err) {
    ctx.setActiveStep("");
    ctx.addLog(err instanceof Error ? `ERROR: ${err.message}` : "ERROR: Unknown error");
  }
}

export async function runHeadersOnly(ctx: BaseActionContext) {
  if (!requireRawPath(ctx.rawPath, ctx.addLog, ctx.setActiveTab)) return;

  if (!ctx.outputPath) {
    ctx.addLog("Please select output folder first.");
    ctx.setActiveTab("import");
    return;
  }

  await runSingleStep("headers", ctx, async () => {
    const data = await callApi(
      "/read-headers",
      {
        raw_path: ctx.rawPath,
        output_path: ctx.outputPath,
      },
      ctx.addLog
    );

    ctx.setDetectedGroups(data.detected_groups ?? []);
  ctx.addLog(`Detected groups: ${data.detected_groups?.length ?? 0}`);

    if (data.first_preview_file) {
      ctx.setFitsPreviewPath(data.first_preview_file);
      ctx.setPreviewMode("fits");
      ctx.setPreviewVersion((v) => v + 1);
    }

    ctx.addLog(`Headers CSV saved: ${data.saved_files?.headers_csv ?? "-"}`);
    ctx.addLog(`Summary CSV saved: ${data.saved_files?.summary_csv ?? "-"}`);

    return data;
  });
}

export async function runCalibrationOnly(ctx: BaseActionContext) {
  if (!requireRawPath(ctx.rawPath, ctx.addLog, ctx.setActiveTab)) return;
  if (!requireOutputPath(ctx.outputPath, ctx.addLog, ctx.setActiveTab)) return;

  await runSingleStep("calibration", ctx, async () => {
    const roleMap =
      Object.keys(ctx.frameRoleMap).length > 0 ? ctx.frameRoleMap : null;

    const data = await callApi(
      "/run-calibration",
      {
        raw_path: ctx.rawPath,
        output_path: ctx.outputPath,
        combine_method: "median",
        frame_role_map: roleMap,
      },
      ctx.addLog
    );

    if (data.status === "need_frame_role_map") {
      ctx.setDetectedGroups(data.detected_groups ?? []);
      ctx.addLog("Please assign bias/dark/flat/light roles, then click Run Calibration again.");
      ctx.setActiveTab("calibration");
      return data;
    }

    ctx.addLog("Calibration completed.");
    ctx.addLog(`Master path: ${data.master_path}`);
    ctx.addLog(`Calibrated path: ${data.calibrated_path}`);

    return data;
  });
}

export async function runTrimOnly(ctx: BaseActionContext) {
  if (!requireOutputPath(ctx.outputPath, ctx.addLog, ctx.setActiveTab)) return;
  await runSingleStep("trim", ctx, () => callApi("/run-trim", trimPayload(ctx.outputPath, ctx.useCommonMinSize), ctx.addLog));
}

export async function runCosmicOnly(ctx: BaseActionContext) {
  if (!requireOutputPath(ctx.outputPath, ctx.addLog, ctx.setActiveTab)) return;
  await runSingleStep("cosmic", ctx, () => callApi("/run-cosmic-ray", cosmicPayload(ctx.outputPath), ctx.addLog));
}

export async function runAlignmentOnly(ctx: BaseActionContext) {
  if (!requireOutputPath(ctx.outputPath, ctx.addLog, ctx.setActiveTab)) return;

  const x = Number(ctx.xStar);
  const y = Number(ctx.yStar);

  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    ctx.addLog("ERROR: Please select or enter reference star position first.");
    ctx.setActiveTab("stars");
    return;
  }

  await runSingleStep("alignment", ctx, () => callApi("/run-alignment", alignmentPayload(ctx.outputPath, x, y), ctx.addLog));
}

export async function runPhotometryOnly(ctx: BaseActionContext) {
  if (!requireOutputPath(ctx.outputPath, ctx.addLog, ctx.setActiveTab)) return;

  const positions = parseStarPositions(ctx.positionsText, ctx.addLog);
  if (!positions) {
    ctx.setActiveTab("stars");
    return;
  }

  await runSingleStep("photometry", ctx, () => callApi("/run-photometry", photometryPayload(ctx.outputPath, positions), ctx.addLog));
}

async function runSingleStep(step: StepKey, ctx: BaseActionContext, action: () => Promise<unknown>) {
  try {
    ctx.setActiveStep(step);
    await action();
    addDoneStep(ctx.setDoneSteps, step);
    ctx.setActiveStep("");
  } catch (err) {
    ctx.setActiveStep("");
    if (err instanceof Error) ctx.addLog(`ERROR: ${err.message}`);
  }
}
