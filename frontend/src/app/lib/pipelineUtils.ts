import type * as React from "react";
import type { AddLog, PipelineStep, StepKey, TabKey } from "../types/pipeline";

export function createLogger(setLogs: React.Dispatch<React.SetStateAction<string[]>>) {
  return function addLog(message: string) {
    const time = new Date().toLocaleTimeString();
    setLogs((prev) => [`${time}  ${message}`, ...prev]);
  };
}

export function requireRawPath(rawPath: string, addLog: AddLog, setActiveTab: (tab: TabKey) => void) {
  if (!rawPath.trim()) {
    addLog("ERROR: Please upload a FITS folder first.");
    setActiveTab("import");
    return false;
  }
  return true;
}

export function requireOutputPath(outputPath: string, addLog: AddLog, setActiveTab: (tab: TabKey) => void) {
  if (!outputPath.trim()) {
    addLog("ERROR: Output folder is not ready. Please upload a FITS folder first.");
    setActiveTab("import");
    return false;
  }
  return true;
}

export function parseStarPositions(positionsText: string, addLog: AddLog) {
  let positions: unknown;
  try {
    positions = JSON.parse(positionsText);
  } catch {
    addLog("ERROR: Star positions format is invalid JSON.");
    return null;
  }

  if (!Array.isArray(positions) || positions.length < 2) {
    addLog("ERROR: Please select at least 2 stars: target + comparison star.");
    return null;
  }

  for (let i = 0; i < positions.length; i++) {
    const item = positions[i];
    if (
      !Array.isArray(item) ||
      item.length !== 2 ||
      !Number.isFinite(Number(item[0])) ||
      !Number.isFinite(Number(item[1]))
    ) {
      addLog(`ERROR: Star position ${i + 1} must be [x, y].`);
      return null;
    }
  }

  return positions.map((item) => [Number(item[0]), Number(item[1])]);
}

export function getRunSteps(pipelineSteps: PipelineStep[], runUntil: StepKey) {
  const endIndex = pipelineSteps.findIndex((s) => s.key === runUntil);
  return pipelineSteps.slice(0, endIndex + 1);
}

export function addDoneStep(
  setDoneSteps: React.Dispatch<React.SetStateAction<string[]>>,
  step: string
) {
  setDoneSteps((prev) => [...new Set([...prev, step])]);
}

export function buildPlotImageUrl(apiBase: string, imagePath: string, previewVersion: number) {
  return imagePath.trim() === ""
    ? ""
    : `${apiBase}/file?path=${encodeURIComponent(imagePath)}&v=${previewVersion}`;
}

export function buildFitsImageUrl(
  apiBase: string,
  fitsPreviewPath: string,
  fitsDownsample: number,
  previewVersion: number
) {
  return fitsPreviewPath.trim() === ""
    ? ""
    : `${apiBase}/preview-fits?path=${encodeURIComponent(
        fitsPreviewPath
      )}&downsample=${fitsDownsample}&v=${previewVersion}`;
}
