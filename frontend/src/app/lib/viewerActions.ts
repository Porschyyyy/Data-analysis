import type * as React from "react";
import type {
  AddLog,
  ClickMode,
  FitsPoint,
  PreviewMode,
  TabKey,
  ToolKey,
  ViewerClickEvent,
} from "../types/pipeline";

export function convertViewerClickToFitsCoordinate({
  event,
  imageElement,
  previewMode,
  zoomLevel,
  fitsDownsample,
}: {
  event: ViewerClickEvent;
  imageElement: HTMLImageElement | null;
  previewMode: PreviewMode;
  zoomLevel: number;
  fitsDownsample: number;
}): FitsPoint | null {
  if (!imageElement) return null;

  const rect = imageElement.getBoundingClientRect();
  const clickX = event.clientX - rect.left;
  const clickY = event.clientY - rect.top;

  if (clickX < 0 || clickY < 0 || clickX > rect.width || clickY > rect.height) {
    return null;
  }

  if (previewMode === "fits") {
    const displayX = clickX / zoomLevel;
    const displayY = clickY / zoomLevel;

    const fitsX = displayX * fitsDownsample;
    const fitsY = (rect.height / zoomLevel - displayY) * fitsDownsample;

    return {
      x: Number(fitsX.toFixed(2)),
      y: Number(fitsY.toFixed(2)),
    };
  }

  return {
    x: Number(clickX.toFixed(2)),
    y: Number(clickY.toFixed(2)),
  };
}

export function handleViewerClick(
  event: ViewerClickEvent,
  ctx: {
    viewerImageElement: HTMLImageElement | null;
    previewMode: PreviewMode;
    zoomLevel: number;
    fitsDownsample: number;
    activeTool: ToolKey;
    clickMode: ClickMode;
    comparisonTargetCount: number;
    setClickMode: (mode: ClickMode) => void;
    positionsText: string;
    addLog: AddLog;
    setXStar: (value: string) => void;
    setYStar: (value: string) => void;
    setPositionsText: React.Dispatch<React.SetStateAction<string>>;
    setZoomLevel: React.Dispatch<React.SetStateAction<number>>;
    setViewerMessage: (message: string) => void;
  }
) {
  const point = convertViewerClickToFitsCoordinate({
    event,
    imageElement: ctx.viewerImageElement,
    previewMode: ctx.previewMode,
    zoomLevel: ctx.zoomLevel,
    fitsDownsample: ctx.fitsDownsample,
  });

  if (!point) return;

  const roundedX = point.x;
  const roundedY = point.y;

  const isTargetMode =
    ctx.clickMode === "target" ||
    ctx.activeTool === "target" ||
    ctx.activeTool === "pick";

  const isComparisonMode =
    ctx.clickMode === "comparison" ||
    ctx.activeTool === "comparison";

  if (ctx.activeTool === "zoom") {
    ctx.setZoomLevel((z) => {
      const nextZoom = z >= 2 ? 1 : z + 0.25;
      ctx.addLog(`Viewer zoom changed to ${nextZoom.toFixed(2)}x`);
      return nextZoom;
    });
    return;
  }

  if (isTargetMode) {
    ctx.setXStar(String(roundedX));
    ctx.setYStar(String(roundedY));

    try {
      const positions = JSON.parse(ctx.positionsText);

      if (Array.isArray(positions)) {
        positions[0] = [roundedX, roundedY];
        ctx.setPositionsText(JSON.stringify(positions, null, 2));
      }
    } catch {
      ctx.setPositionsText(JSON.stringify([[roundedX, roundedY]], null, 2));
    }

    const label = ctx.activeTool === "pick" ? "Reference star" : "Target";

    ctx.addLog(`${label} selected at x=${roundedX}, y=${roundedY}`);
    ctx.setViewerMessage(`${label} selected: x=${roundedX}, y=${roundedY}`);
    return;
  }

  if (isComparisonMode) {
    try {
      const positions = JSON.parse(ctx.positionsText);

      if (Array.isArray(positions)) {
        positions.push([roundedX, roundedY]);
        const comparisonCount = positions.length - 1;

        ctx.setPositionsText(JSON.stringify(positions, null, 2));

        if (comparisonCount >= ctx.comparisonTargetCount) {
          ctx.setClickMode(null);

          ctx.addLog(
            `Comparison selection completed with ${comparisonCount} stars`
          );

          ctx.setViewerMessage(
            `Comparison selection complete (${comparisonCount} stars)`
          );

          return;
        }
      }
    } catch {
      ctx.setPositionsText(
        JSON.stringify([[0, 0], [roundedX, roundedY]], null, 2)
      );
    }

    ctx.addLog(`Comparison star added at x=${roundedX}, y=${roundedY}`);
    ctx.setViewerMessage(`Comparison star added: x=${roundedX}, y=${roundedY}`);
    return;
  }

  ctx.addLog(
    `Viewer clicked at x=${roundedX}, y=${roundedY} with tool ${ctx.activeTool}`
  );
  ctx.setViewerMessage(
    `Clicked x=${roundedX}, y=${roundedY} using ${ctx.activeTool} tool`
  );
}

export function handleTopMenuClick(
  menu: string,
  ctx: {
    addLog: AddLog;
    setActiveTab: (tab: TabKey) => void;
    setPreviewMode: (mode: PreviewMode) => void;
    setViewerMessage: (message: string) => void;
    chooseRawFolder: () => void;
  }
) {
  if (menu === "file") {
    ctx.setActiveTab("import");
    ctx.setViewerMessage("File menu: choose raw FITS folder.");
    ctx.addLog("Menu selected: File / Import");
    ctx.chooseRawFolder();
    return;
  }

  if (menu === "image") {
    ctx.setActiveTab("stars");
    ctx.setPreviewMode("fits");
    ctx.setViewerMessage("Image menu: FITS preview / star selection.");
    ctx.addLog("Menu selected: Image");
    return;
  }

  if (menu === "process") {
    ctx.setActiveTab("processing");
    ctx.setViewerMessage("Process menu: trim, cosmic ray removal, alignment.");
    ctx.addLog("Menu selected: Process");
    return;
  }

  if (menu === "analyze") {
    ctx.setActiveTab("photometry");
    ctx.setViewerMessage("Analyze menu: photometry tools.");
    ctx.addLog("Menu selected: Analyze / Photometry");
    return;
  }

  if (menu === "window" || menu === "help") {
    ctx.setActiveTab("results");
    ctx.setViewerMessage("Results / Help opened.");
    ctx.addLog("Menu selected: Results / Help");
  }
}

export function handleToolClick(
  tool: ToolKey,
  ctx: {
    addLog: AddLog;
    runPipeline: () => void;
    setActiveTool: (tool: ToolKey) => void;
    setActiveTab: (tab: TabKey) => void;
    setPreviewMode: (mode: PreviewMode) => void;
    setClickMode: (mode: ClickMode) => void;
    setZoomLevel: React.Dispatch<React.SetStateAction<number>>;
    setViewerMessage: (message: string) => void;
  }
) {
  ctx.setActiveTool(tool);

  if (tool === "move") {
    ctx.setClickMode(null);
    ctx.setViewerMessage("Move tool selected.");
    ctx.addLog("Tool selected: Move");
    return;
  }

  if (tool === "zoom") {
    ctx.setClickMode(null);
    ctx.setZoomLevel((z) => {
      const nextZoom = z >= 2 ? 1 : z + 0.25;
      ctx.addLog(`Zoom changed to ${nextZoom.toFixed(2)}x`);
      return nextZoom;
    });
    ctx.setViewerMessage("Zoom tool selected.");
    return;
  }

  if (tool === "fit") {
    ctx.setClickMode(null);
    ctx.setZoomLevel(1);
    ctx.setViewerMessage("View reset to 1.00x.");
    ctx.addLog("Tool selected: Fit / reset view");
    return;
  }

  if (tool === "pick") {
    ctx.setActiveTab("stars");
    ctx.setPreviewMode("fits");
    ctx.setClickMode("target");
    ctx.setViewerMessage("Pick reference star: click one star.");
    ctx.addLog("Tool selected: Pick reference star");
    return;
  }

  if (tool === "target") {
    ctx.setActiveTab("stars");
    ctx.setPreviewMode("fits");
    ctx.setClickMode("target");
    ctx.setViewerMessage("Target mode: click target star.");
    ctx.addLog("Tool selected: Target star");
    return;
  }

  if (tool === "comparison") {
    ctx.setActiveTab("stars");
    ctx.setPreviewMode("fits");
    ctx.setClickMode("comparison");
    ctx.setViewerMessage("Comparison mode: click comparison stars.");
    ctx.addLog("Tool selected: Comparison star");
    return;
  }

  if (tool === "aperture") {
    ctx.setActiveTab("photometry");
    ctx.setClickMode(null);
    ctx.setViewerMessage("Aperture settings opened.");
    ctx.addLog("Tool selected: Aperture");
    return;
  }

  if (tool === "photometry") {
    ctx.setActiveTab("photometry");
    ctx.setClickMode(null);
    ctx.setViewerMessage("Photometry tab opened.");
    ctx.addLog("Tool selected: Photometry");
    return;
  }

  if (tool === "plot") {
    ctx.setActiveTab("lightcurve");
    ctx.setPreviewMode("plot");
    ctx.setClickMode(null);
    ctx.setViewerMessage("Light curve tab opened.");
    ctx.addLog("Tool selected: Plot");
    return;
  }

  if (tool === "run") {
    ctx.setClickMode(null);
    ctx.setViewerMessage("Running pipeline.");
    ctx.addLog("Tool selected: Run pipeline");
    ctx.runPipeline();
  }
}