"use client";

import { useEffect, useRef, useState } from "react";
import { listFitsRequest } from "./lib/pipelineApi"
import { StatusFooter } from "./components/StatusFooter";
import { Toolbar } from "./components/Toolbar";
import { TabBar } from "./components/TabBar";
import { ImageViewer } from "./components/ImageViewer";
import { ControlPanelHeader } from "./components/ControlPanelHeader";
import { ImportPanel } from "./components/panels/ImportPanel";
import { CalibrationPanel } from "./components/panels/CalibrationPanel";
import { ProcessingPanel } from "./components/panels/ProcessingPanel";
import { StarSelectionPanel } from "./components/panels/StarSelectionPanel";
import { PhotometryPanel } from "./components/panels/PhotometryPanel";
import { LightCurvePanel } from "./components/panels/LightCurvePanel";

import {
  API_BASE,
  defaultPositionsText,
  pipelineSteps,
  tabs,
  toolbarButtons,
  topMenuButtons,
} from "./lib/constants";
import {
  buildFitsImageUrl,
  buildPlotImageUrl,
  createLogger,
} from "./lib/pipelineUtils";
import {
  chooseFolder as chooseFolderAction,
  plotOnly as plotOnlyAction,
  runAlignmentOnly as runAlignmentOnlyAction,
  runCalibrationOnly as runCalibrationOnlyAction,
  runCosmicOnly as runCosmicOnlyAction,
  runHeadersOnly as runHeadersOnlyAction,
  runPhotometryOnly as runPhotometryOnlyAction,
  runPipeline as runPipelineAction,
  runTrimOnly as runTrimOnlyAction,
} from "./lib/pipelineActions";
import {
  handleToolClick as handleToolClickAction,
  handleTopMenuClick as handleTopMenuClickAction,
  handleViewerClick as handleViewerClickAction,
} from "./lib/viewerActions";
import type { ClickMode, PlotStyle, PreviewMode, StepKey, TabKey, ToolKey, TopMenuKey, ViewerClickEvent } from "./types/pipeline";

export default function Home() {
  const [rawPath, setRawPath] = useState("");
  const [outputPath, setOutputPath] = useState("");

  const [activeTab, setActiveTab] = useState<TabKey>("import");
  const [runUntil, setRunUntil] = useState<StepKey>("lightcurve");
  const [activeStep, setActiveStep] = useState("");
  const [doneSteps, setDoneSteps] = useState<string[]>([]);

  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [totalImages, setTotalImages] = useState(0);
  const [processingMessage, setProcessingMessage] = useState("Ready");

  const [logs, setLogs] = useState<string[]>(["Ready."]);

  const [isBackendRunning, setIsBackendRunning] = useState(false);

  const [xStar, setXStar] = useState("");
  const [yStar, setYStar] = useState("");
  const [positionsText, setPositionsText] = useState(defaultPositionsText);
  const [selectedMarkers, setSelectedMarkers] = useState<
    { x: number; y: number; type: "target" | "comparison" | "reference" }[]
  >([]);
  const [comparisonTargetCount, setComparisonTargetCount] = useState(3);

  const [plotStyle, setPlotStyle] = useState<PlotStyle>("1");
  const [graphTitle, setGraphTitle] = useState("WASP-12b Light Curve");
  const [usePreset, setUsePreset] = useState(true);

  const [imagePath, setImagePath] = useState("");
  const [previewMode, setPreviewMode] = useState<PreviewMode>("plot");
  const [fitsPreviewPath, setFitsPreviewPath] = useState("");
  const [fitsFiles, setFitsFiles] = useState<string[]>([])
  const [detectedGroups, setDetectedGroups] = useState<
    { group_name: string; n_files: number; example_files: string[] }[]
  >([])

  const [frameRoleMap, setFrameRoleMap] = useState<Record<string, string>>({})
  const [imageProcessingPreviewStep, setImageProcessingPreviewStep] =
    useState<"calibrated" | "trimmed" | "cosmic_cleaned" | "aligned">("calibrated")
  const [fitsDownsample, setFitsDownsample] = useState(8);
  const [previewVersion, setPreviewVersion] = useState(0);

  const viewerImageRef = useRef<HTMLImageElement | null>(null);

  const [activeTool, setActiveTool] = useState<ToolKey>("move");
  const [zoomLevel, setZoomLevel] = useState(1);
  const [viewerMessage, setViewerMessage] = useState("Select a tool from the toolbar.");
  const [clickMode, setClickMode] = useState<ClickMode>(null);

  const addLog = createLogger(setLogs);

  const plotImageUrl = buildPlotImageUrl(API_BASE, imagePath, previewVersion);
  const fitsImageUrl = buildFitsImageUrl(API_BASE, fitsPreviewPath, fitsDownsample, previewVersion);
  const imageUrl = previewMode === "fits" ? fitsImageUrl : plotImageUrl;

  const [useCommonMinSize, setUseCommonMinSize] = useState(true);

  const actionContext = {
    rawPath,
    outputPath,
    xStar,
    yStar,
    positionsText,
    plotStyle,
    graphTitle,
    usePreset,
    addLog,
    setActiveTab,
    setActiveStep,
    setDoneSteps,
    setImagePath,
    setFitsPreviewPath,
    setPreviewMode,
    setPreviewVersion,
    detectedGroups,
    setDetectedGroups,
    frameRoleMap,
    setFrameRoleMap,
    useCommonMinSize,
  };

  const chooseFolder = (target: "raw" | "output") =>
    chooseFolderAction(target, {
      rawPath,
      outputPath,
      addLog,
      setRawPath,
      setOutputPath,
      setImagePath,
      setFitsPreviewPath,
    });

  const runPipeline = () => runPipelineAction({ ...actionContext, runUntil });
  const plotOnly = (writeDoneLog = true) => plotOnlyAction(actionContext, writeDoneLog);
  const runHeadersOnly = () => runHeadersOnlyAction(actionContext);
  const runCalibrationOnly = () => runCalibrationOnlyAction(actionContext);
  const runTrimOnly = () => runTrimOnlyAction(actionContext);
  const runCosmicOnly = () => runCosmicOnlyAction(actionContext);
  const runAlignmentOnly = () => runAlignmentOnlyAction(actionContext);
  const runPhotometryOnly = () => runPhotometryOnlyAction(actionContext);

  const handleTopMenuClick = (menu: TopMenuKey) =>
    handleTopMenuClickAction(menu, {
      addLog,
      setActiveTab,
      setPreviewMode,
      setViewerMessage,
      chooseRawFolder: () => chooseFolder("raw"),
    });

  const handleToolClick = (tool: ToolKey) =>
    handleToolClickAction(tool, {
      addLog,
      runPipeline,
      setActiveTool,
      setActiveTab,
      setPreviewMode,
      setClickMode,
      setZoomLevel,
      setViewerMessage,
    });

  const handleViewerClick = (event: ViewerClickEvent) =>
    handleViewerClickAction(event, {
      viewerImageElement: viewerImageRef.current,
      previewMode,
      zoomLevel,
      fitsDownsample,
      activeTool,
      clickMode,
      comparisonTargetCount,
      setClickMode,
      positionsText,
      addLog,
      setXStar,
      setYStar,
      setPositionsText,
      setZoomLevel,
      setViewerMessage,
      setSelectedMarkers,
      selectedMarkers,
    });

  const [trimSummary, setTrimSummary] = useState<{
    n_files: number;
    size_counts: { width: number; height: number; count: number }[];
    crop_target: { width: number; height: number };
  } | null>(null);

  const loadTrimSummary = async () => {
  if (!outputPath) {
    addLog("Please select output folder first.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/trim-summary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input_path: `${outputPath}/calibrated`,
        output_path: `${outputPath}/trimmed`,
        use_common_min_size: useCommonMinSize,
      }),
    });

    if (!res.ok) {
      const errorText = await res.text();
      addLog(`Trim summary failed: ${errorText}`);
      return;
    }

    const data = await res.json();
    setTrimSummary(data);
    addLog(`Trim summary loaded: ${data.n_files} files`);
  } catch {
    addLog("Cannot connect to backend or /trim-summary does not exist. Restart FastAPI and check api.py.");
  }
};

  async function loadFitsPreviewFromFolder(folderPath: string) {
  try {
    const data = await listFitsRequest(folderPath, addLog)

    setFitsFiles(data.files)

    if (data.first_file) {
      setFitsPreviewPath(data.first_file)
      setPreviewMode("fits")
      setPreviewVersion((v) => v + 1)
      addLog(`Preview loaded: ${data.first_file}`)
    } else {
      addLog(`No FITS files found in: ${folderPath}`)
    }
  } catch (err) {
    addLog(
      err instanceof Error
        ? `ERROR: ${err.message}`
        : "ERROR: Cannot load FITS preview"
    )
  }
}

function previewCurrentTab() {
  if (activeTab === "import") {
    if (!rawPath) {
      addLog("Please select raw folder first.")
      return
    }

    void loadFitsPreviewFromFolder(rawPath)
    return
  }

  if (!outputPath) {
    addLog("Please select output folder first.")
    return
  }

  if (activeTab === "calibration") {
    addLog("Preview calibrated images. If not found, run calibration first.")
    void loadFitsPreviewFromFolder(`${outputPath}/calibrated`)
    return
  }

  if (activeTab === "processing") {
    addLog(`Preview processing step: ${imageProcessingPreviewStep}`)
    void loadFitsPreviewFromFolder(`${outputPath}/${imageProcessingPreviewStep}`)
    return
  }

  if (activeTab === "stars") {
    addLog("Preview cosmic cleaned images for star selection.")
    void loadFitsPreviewFromFolder(`${outputPath}/cosmic_cleaned`)
    return
  }

  if (activeTab === "photometry") {
    addLog("Preview aligned images for photometry.")
    void loadFitsPreviewFromFolder(`${outputPath}/aligned`)
    return
  }
}

useEffect(() => {
  if (!rawPath) return

  if (activeTab === "import") {
    previewCurrentTab()
  }
}, [activeTab, imageProcessingPreviewStep])

const comparisonCount = selectedMarkers.filter(
  (marker) => marker.type === "comparison"
).length;

const progressPercent =
  totalImages > 0
    ? Math.min(100, Math.round((currentImageIndex / totalImages) * 100))
    : 0;

const statusLabel =
  activeStep === "idle" ? "Ready" : "Processing";

const rawLabel = rawPath ? "Selected" : "None";
const outputLabel = outputPath ? "Selected" : "None";

useEffect(() => {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/progress`);
      const data = await res.json();

      setCurrentImageIndex(data.current ?? 0);
      setTotalImages(data.total ?? 0);
      setProcessingMessage(data.message ?? "Ready");
      setIsBackendRunning(data.running ?? false);
    } catch {
      // backend ยังไม่เปิด ไม่ต้องทำอะไร
    }
  }, 500);

  return () => clearInterval(interval);
}, []);

const undoLastMarker = () => {
  setSelectedMarkers((prev) => prev.slice(0, -1));

  setPositionsText((prev) => {
    try {
      const positions = JSON.parse(prev);
      if (!Array.isArray(positions)) return prev;
      positions.pop();
      return JSON.stringify(positions, null, 2);
    } catch {
      return prev;
    }
  });
};

const clearComparisonMarkers = () => {
  setSelectedMarkers((prev) => prev.filter((m) => m.type !== "comparison"));

  setPositionsText((prev) => {
    try {
      const positions = JSON.parse(prev);
      if (!Array.isArray(positions)) return prev;
      return JSON.stringify(positions.slice(0, 1), null, 2);
    } catch {
      return prev;
    }
  });
};

const clearAllMarkers = () => {
  setSelectedMarkers([]);
  setPositionsText("[]");
  setXStar("");
  setYStar("");
};


  return (
    <main className="min-h-screen bg-slate-100 p-4 text-slate-900">
      <div className="mx-auto flex max-w-375 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl">
        <header className="border-b border-slate-200 bg-white">
          <Toolbar
            toolbarButtons={toolbarButtons}
            activeTool={activeTool}
            onToolClick={handleToolClick}
          />
      </header>

      <section className="border-b border-slate-200 bg-linear-to-r from-slate-950 via-slate-900 to-blue-950 px-6 py-5 text-white">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">AstroPipeline</h1>
            <p className="mt-1 text-sm text-blue-100">
              FITS calibration · photometry · light curve · transit analysis
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full bg-white/10 px-3 py-1 text-blue-50">
              API: {API_BASE}
            </span>

            <span className="rounded-full bg-emerald-400/20 px-3 py-1 text-emerald-100">
              Active: {activeStep ?? "Idle"}
            </span>
          </div>
        </div>
      </section>

      <nav className="border-b border-slate-400 bg-[#e8e8e8] px-2 pt-2">
        <div className="flex flex-wrap gap-1">
          <TabBar
            tabs={tabs}
            activeTab={activeTab}
            onTabClick={setActiveTab}
          />
        </div>
      </nav>

      <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <ImageViewer
          viewerImageRef={viewerImageRef}
          previewMode={previewMode}
          activeTool={activeTool}
          previewUrl={imageUrl}
          imagePath={imagePath}
          fitsPreviewPath={fitsPreviewPath}
          viewerMessage={viewerMessage}
          zoomLevel={zoomLevel}
          onViewerClick={handleViewerClick}
          onRefresh={() => setPreviewVersion((v) => v + 1)}
          selectedMarkers={selectedMarkers}
          fitsDownsample={fitsDownsample}
        />

        <aside className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <ControlPanelHeader
            activeTab={activeTab}
            onPreview={previewCurrentTab}
          />

          <div className="max-h-190 overflow-auto space-y-4 p-4">
            {activeTab === "import" && (
              <ImportPanel
                rawPath={rawPath}
                outputPath={outputPath}
                setRawPath={setRawPath}
                setOutputPath={setOutputPath}
                chooseRawFolder={() => chooseFolder("raw")}
                chooseOutputFolder={() => chooseFolder("output")}
                runHeadersOnly={runHeadersOnly}
              />
            )}

            {activeTab === "calibration" && (
              <CalibrationPanel
                detectedGroups={detectedGroups}
                frameRoleMap={frameRoleMap}
                setFrameRoleMap={setFrameRoleMap}
                runCalibrationOnly={runCalibrationOnly}
              />
            )}

            {activeTab === "processing" && (
              <ProcessingPanel
                imageProcessingPreviewStep={imageProcessingPreviewStep}
                setImageProcessingPreviewStep={setImageProcessingPreviewStep}

                runTrimOnly={runTrimOnly}
                trimSummary={trimSummary}
                loadTrimSummary={loadTrimSummary}

                runCosmicRayOnly={runCosmicOnly}
                runAlignmentOnly={runAlignmentOnly}

                xStar={xStar}
                yStar={yStar}
                setXStar={setXStar}
                setYStar={setYStar}

                useCommonMinSize={useCommonMinSize}
                setUseCommonMinSize={setUseCommonMinSize}

              />
            )}

            {activeTab === "stars" && (
              <StarSelectionPanel
                fitsPreviewPath={fitsPreviewPath}
                setFitsPreviewPath={setFitsPreviewPath}
                fitsFiles={fitsFiles}
                fitsDownsample={fitsDownsample}
                setFitsDownsample={setFitsDownsample}
                xStar={xStar}
                yStar={yStar}
                setXStar={setXStar}
                setYStar={setYStar}
                positionsText={positionsText}
                setPositionsText={setPositionsText}
                comparisonTargetCount={comparisonTargetCount}
                setComparisonTargetCount={setComparisonTargetCount}
                comparisonCount={comparisonCount}
                loadFitsPreview={() => {
                  setPreviewMode("fits");
                  setPreviewVersion((v) => v + 1);
                  addLog("FITS preview refreshed.");
                }}
                undoLastMarker={undoLastMarker}
                clearComparisonMarkers={clearComparisonMarkers}
                clearAllMarkers={clearAllMarkers}
              />
            )}

            {activeTab === "photometry" && (
              <PhotometryPanel
                positionsText={positionsText}
                setPositionsText={setPositionsText}
                runPhotometryOnly={runPhotometryOnly}
              />
            )}

            {activeTab === "lightcurve" && (
              <LightCurvePanel
                imagePath={imagePath}
                setImagePath={setImagePath}
                runPlotLightCurve={plotOnly}
              />
            )}

            <div className="mt-6 border-t border-slate-300 pt-4">
              <h3 className="mb-2 text-sm font-bold">Run until</h3>

              <select
                value={runUntil}
                onChange={(e) => setRunUntil(e.target.value as StepKey)}
                className="w-full border border-slate-400 px-2 py-1 text-sm"
              >
                {pipelineSteps.map((step) => (
                  <option key={step.key} value={step.key}>
                    {step.label}
                  </option>
                ))}
              </select>

              <button
                type="button"
                onClick={runPipeline}
                className="mt-3 w-full border border-red-800 bg-red-700 px-3 py-2 text-sm font-semibold text-white hover:bg-red-600"
              >
                Run Pipeline
              </button>
            </div>
          </div>
        </aside>
      </div>

      <StatusFooter
        currentImageIndex={currentImageIndex}
        totalImages={totalImages}
        processingMessage={processingMessage}
        isBackendRunning={isBackendRunning}
        activeTool={activeTool}
        zoomLevel={zoomLevel}
        rawPath={rawPath}
        outputPath={outputPath}
        doneStepsLength={doneSteps.length}
      />

      </div>
    </main>
  );
}