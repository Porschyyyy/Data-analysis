"use client";

import { useEffect, useRef, useState } from "react";
import { listFitsRequest } from "./lib/pipelineApi"
import { StatusFooter } from "./components/StatusFooter";
import { Toolbar } from "./components/Toolbar";
import { TabBar } from "./components/TabBar";
import { ImageViewer } from "./components/ImageViewer";
import { ControlPanelHeader } from "./components/ControlPanelHeader";
import { ImportPanel } from "./components/panels/ImportPanel";

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
    });

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

const comparisonCount = (() => {
  try {
    const positions = JSON.parse(positionsText);

    if (!Array.isArray(positions)) return 0;

    return Math.max(positions.length - 1, 0);
  } catch {
    return 0;
  }
})();

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
          onResults={() => setActiveTab("results")}
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
              <div className="space-y-4">
                <h3 className="text-lg font-bold">Calibration</h3>

                <p className="text-sm text-slate-500">
                  Assign each detected group, then run calibration to create master files and calibrated light frames.
                </p>

                {detectedGroups.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="font-semibold">Assign frame roles</h4>

                    {detectedGroups.map((group) => (
                      <div
                        key={group.group_name}
                        className="rounded-lg border border-slate-200 bg-white p-3"
                      >
                        <p className="text-sm font-semibold">{group.group_name}</p>
                        <p className="text-xs text-slate-500">Files: {group.n_files}</p>
                        <p className="text-xs text-slate-500">
                          Example: {group.example_files.join(", ")}
                        </p>

                        <select
                          value={frameRoleMap[group.group_name] ?? "skip"}
                          onChange={(e) =>
                            setFrameRoleMap((prev) => ({
                              ...prev,
                              [group.group_name]: e.target.value,
                            }))
                          }
                          className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                        >
                          <option value="skip">skip</option>
                          <option value="bias">bias</option>
                          <option value="dark">dark</option>
                          <option value="flat">flat</option>
                          <option value="light">light</option>
                        </select>
                      </div>
                    ))}
                  </div>
                )}

                <button
                  type="button"
                  onClick={runCalibrationOnly}
                  className="w-full border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  Calibration
                </button>
              </div>
            )}

            {activeTab === "processing" && (
              <div className="space-y-4">
                <h3 className="text-lg font-bold">Image Processing</h3>

                <label className="block">
                  <span className="text-sm font-medium">
                    Preview processing step
                  </span>

                  <select
                    value={imageProcessingPreviewStep}
                    onChange={(e) =>
                      setImageProcessingPreviewStep(
                        e.target.value as
                          | "calibrated"
                          | "trimmed"
                          | "cosmic_cleaned"
                          | "aligned"
                      )
                    }
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                  >
                    <option value="calibrated">Calibrated</option>
                    <option value="trimmed">Trimmed</option>
                    <option value="cosmic_cleaned">Cosmic cleaned</option>
                    <option value="aligned">Aligned</option>
                  </select>
                </label>

                <button
                  type="button"
                  onClick={runTrimOnly}
                  className="w-full border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  Trim
                </button>

                <button
                  type="button"
                  onClick={runCosmicOnly}
                  className="w-full border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  Cosmic Ray Removal
                </button>

                <button
                  type="button"
                  onClick={runAlignmentOnly}
                  className="w-full border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  Alignment
                </button>
              </div>
            )}

            {activeTab === "stars" && (
              <div className="space-y-4">
                <h3 className="text-lg font-bold">Star Selection</h3>

                <label className="block">
                  <span className="text-sm font-medium">FITS preview path</span>
                  <input
                    value={fitsPreviewPath}
                    onChange={(e) => setFitsPreviewPath(e.target.value)}
                    placeholder={`${outputPath}/aligned/.../file.fits`}
                    className="mt-1 w-full border border-slate-400 px-2 py-1 text-sm"
                  />

                  <select
                    value={fitsPreviewPath}
                    onChange={(e) => {
                      setFitsPreviewPath(e.target.value)
                      setPreviewMode("fits")
                      setPreviewVersion((v) => v + 1)
                    }}
                    className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                  >
                    <option value="">Select FITS file...</option>

                    {fitsFiles.map((file) => (
                      <option key={file} value={file}>
                        {file}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="text-sm font-medium">
                    Preview downsample
                  </span>
                  <input
                    type="number"
                    value={fitsDownsample}
                    onChange={(e) => setFitsDownsample(Number(e.target.value))}
                    className="mt-1 w-full border border-slate-400 px-2 py-1 text-sm"
                  />
                </label>

                <button
                  onClick={() => {
                    setPreviewMode("fits");
                    setPreviewVersion((v) => v + 1);
                    addLog("FITS preview refreshed.");
                  }}
                  className="w-full border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  Load FITS Preview
                </button>

                <div className="grid grid-cols-2 gap-3">
                  <label>
                    <span className="text-sm font-medium">x_star</span>
                    <input
                      value={xStar}
                      onChange={(e) => setXStar(e.target.value)}
                      className="mt-1 w-full border border-slate-400 px-2 py-1 text-sm"
                    />
                  </label>

                  <label>
                    <span className="text-sm font-medium">y_star</span>
                    <input
                      value={yStar}
                      onChange={(e) => setYStar(e.target.value)}
                      className="mt-1 w-full border border-slate-400 px-2 py-1 text-sm"
                    />
                  </label>
                </div>

                <label className="block">
                  <span className="text-sm font-medium">
                    Comparison stars needed
                  </span>

                  <select
                    value={comparisonTargetCount}
                    onChange={(e) =>
                      setComparisonTargetCount(Number(e.target.value))
                    }
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    {[1,2,3,4,5,6,7,8].map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                </label>

                <p className="text-xs text-slate-500">
                  Selected: {comparisonCount} / {comparisonTargetCount}
                </p>

                <label className="block">
                  <span className="text-sm font-medium">
                    Photometry positions JSON
                  </span>
                  <textarea
                    value={positionsText}
                    onChange={(e) => setPositionsText(e.target.value)}
                    rows={9}
                    className="mt-1 w-full border border-slate-400 px-2 py-1 font-mono text-xs"
                  />
                </label>

                <p className="text-xs text-slate-500">
                  ตัวแรกคือ target star ตัวถัดไปคือ comparison stars
                </p>
              </div>
            )}

            {activeTab === "photometry" && (
              <div className="space-y-4">
                <h3 className="text-lg font-bold">Photometry</h3>
                <p className="text-sm text-slate-500">
                  Uses auto FWHM aperture, auto annulus and centroid recentering.
                </p>

                <button
                  type="button"
                  onClick={runPhotometryOnly}
                  className="w-full border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  Photometry
                </button>
              </div>
            )}

            {activeTab === "lightcurve" && (
              <div className="space-y-4">
                <h3 className="text-lg font-bold">Light Curve</h3>

                <label className="block">
                  <span className="text-sm font-medium">Graph title</span>
                  <input
                    value={graphTitle}
                    onChange={(e) => setGraphTitle(e.target.value)}
                    className="mt-1 w-full border border-slate-400 px-2 py-1 text-sm"
                  />
                </label>

                <label className="block">
                  <span className="text-sm font-medium">Plot style</span>
                  <select
                    value={plotStyle}
                    onChange={(e) => setPlotStyle(e.target.value as "1" | "2")}
                    className="mt-1 w-full border border-slate-400 px-2 py-1 text-sm"
                  >
                    <option value="1">Academic: points + error bars</option>
                    <option value="2">Line: clean line only</option>
                  </select>
                </label>

                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={usePreset}
                    onChange={(e) => setUsePreset(e.target.checked)}
                  />
                  Use WASP-12b ephemeris preset
                </label>

                <button
                  type="button"
                  onClick={() => plotOnly(true)}
                  className="w-full border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  Plot only
                </button>

                <label className="block">
                  <span className="text-sm font-medium">
                    Preview image path
                  </span>
                  <input
                    value={imagePath}
                    onChange={(e) => setImagePath(e.target.value)}
                    className="mt-1 w-full border border-slate-400 px-2 py-1 text-sm"
                  />
                </label>
              </div>
            )}

            {activeTab === "results" && (
              <div className="space-y-4">
                <h3 className="text-lg font-bold">Results / Log</h3>

                <label className="block">
                  <span className="text-sm font-medium">
                    Preview image path
                  </span>
                  <input
                    value={imagePath}
                    onChange={(e) => setImagePath(e.target.value)}
                    className="mt-1 w-full border border-slate-400 px-2 py-1 text-sm"
                  />
                </label>

                <button
                  type="button"
                  onClick={() => setPreviewVersion((v) => v + 1)}
                  className="w-full border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  Refresh Preview
                </button>

                <div className="border border-slate-500 bg-slate-950 p-3 text-white">
                  <h4 className="mb-2 text-sm font-semibold">Run Log</h4>
                  <div className="h-72 overflow-auto font-mono text-xs">
                    {logs.map((log, index) => (
                      <div key={index}>{log}</div>
                    ))}
                  </div>
                </div>
              </div>
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