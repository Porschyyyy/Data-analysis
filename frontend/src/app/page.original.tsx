"use client";

import { useRef, useState, type MouseEvent } from "react";

const API_BASE = "http://127.0.0.1:8000";

const pipelineSteps = [
  { key: "headers", label: "Import / Headers" },
  { key: "calibration", label: "Master + Calibrated" },
  { key: "trim", label: "Trim" },
  { key: "cosmic", label: "Cosmic Ray" },
  { key: "alignment", label: "Alignment" },
  { key: "photometry", label: "Photometry" },
  { key: "lightcurve", label: "Light Curve" },
];

type StepKey =
  | "headers"
  | "calibration"
  | "trim"
  | "cosmic"
  | "alignment"
  | "photometry"
  | "lightcurve";

type TabKey =
  | "import"
  | "calibration"
  | "processing"
  | "stars"
  | "photometry"
  | "lightcurve"
  | "results";

type ToolKey =
  | "rectangle"
  | "oval"
  | "line"
  | "angle"
  | "move"
  | "text"
  | "zoom"
  | "pan"
  | "target"
  | "comparison"
  | "aperture"
  | "plot"
  | "run";

type TopMenuKey =
  | "file"
  | "edit"
  | "image"
  | "process"
  | "analyze"
  | "plugins"
  | "window"
  | "help";

const tabs: { key: TabKey; label: string }[] = [
  { key: "import", label: "Import" },
  { key: "calibration", label: "Calibration" },
  { key: "processing", label: "Image Processing" },
  { key: "stars", label: "Star Selection" },
  { key: "photometry", label: "Photometry" },
  { key: "lightcurve", label: "Light Curve" },
  { key: "results", label: "Results / Log" },
];

export default function Home() {
  const [rawPath, setRawPath] = useState("");
  const [outputPath, setOutputPath] = useState("");

  const [activeTab, setActiveTab] = useState<TabKey>("import");
  const [runUntil, setRunUntil] = useState<StepKey>("lightcurve");
  const [activeStep, setActiveStep] = useState("");
  const [doneSteps, setDoneSteps] = useState<string[]>([]);
  const [logs, setLogs] = useState<string[]>(["Ready."]);

  const [xStar, setXStar] = useState("");
  const [yStar, setYStar] = useState("");

  const [positionsText, setPositionsText] = useState(
    `[
  [1110.28, 868.72],
  [1286.90, 2525.87],
  [2918.07, 3066.12]
]`
  );

  const [plotStyle, setPlotStyle] = useState<"1" | "2">("1");
  const [graphTitle, setGraphTitle] = useState("WASP-12b Light Curve");
  const [usePreset, setUsePreset] = useState(true);

  const [imagePath, setImagePath] = useState("");
  const [previewMode, setPreviewMode] = useState<"plot" | "fits">("plot");

  const [fitsPreviewPath, setFitsPreviewPath] = useState("");
  const [fitsDownsample, setFitsDownsample] = useState(8);
  const [previewVersion, setPreviewVersion] = useState(0);

  const viewerImageRef = useRef<HTMLImageElement | null>(null);

  const [activeTool, setActiveTool] = useState<ToolKey>("move");
  const [zoomLevel, setZoomLevel] = useState(1);
  const [viewerMessage, setViewerMessage] = useState(
    "Select a tool from the toolbar."
  );
  const [clickMode, setClickMode] = useState<"target" | "comparison" | null>(
    null
  );

  const plotImageUrl =
    imagePath.trim() === ""
      ? ""
      : `${API_BASE}/file?path=${encodeURIComponent(
          imagePath
        )}&v=${previewVersion}`;

  const fitsImageUrl =
    fitsPreviewPath.trim() === ""
      ? ""
      : `${API_BASE}/preview-fits?path=${encodeURIComponent(
          fitsPreviewPath
        )}&downsample=${fitsDownsample}&v=${previewVersion}`;

  const imageUrl = previewMode === "fits" ? fitsImageUrl : plotImageUrl;

  const topMenuButtons: {
    key: TopMenuKey;
    label: string;
  }[] = [
    { key: "file", label: "File" },
    { key: "edit", label: "Edit" },
    { key: "image", label: "Image" },
    { key: "process", label: "Process" },
    { key: "analyze", label: "Analyze" },
    { key: "plugins", label: "Plugins" },
    { key: "window", label: "Window" },
    { key: "help", label: "Help" },
  ];

  const toolbarButtons: {
    key: ToolKey;
    label: string;
    title: string;
  }[] = [
    { key: "rectangle", label: "□", title: "Rectangle selection" },
    { key: "oval", label: "○", title: "Oval / aperture selection" },
    { key: "line", label: "/", title: "Line profile tool" },
    { key: "angle", label: "∠", title: "Angle measurement tool" },
    { key: "move", label: "✣", title: "Move selection tool" },
    { key: "text", label: "A", title: "Text annotation tool" },
    { key: "zoom", label: "⌕", title: "Zoom tool" },
    { key: "pan", label: "✋", title: "Pan tool" },
    { key: "target", label: "◎", title: "Select target star" },
    { key: "comparison", label: "⊙", title: "Select comparison star" },
    { key: "aperture", label: "▥", title: "Aperture settings" },
    { key: "plot", label: "P", title: "Plot light curve" },
    { key: "run", label: "≫", title: "Run pipeline" },
  ];

  function addLog(message: string) {
    const time = new Date().toLocaleTimeString();
    setLogs((prev) => [`${time}  ${message}`, ...prev]);
  }

  function requireRawPath() {
    if (!rawPath.trim()) {
      addLog("ERROR: Please select raw folder first.");
      setActiveTab("import");
      return false;
    }

    return true;
  }

  function requireOutputPath() {
    if (!outputPath.trim()) {
      addLog("ERROR: Please select output folder first.");
      setActiveTab("import");
      return false;
    }

    return true;
  }

  function parseStarPositions() {
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

  async function callApi(endpoint: string, body: unknown) {
    addLog(`POST ${endpoint}`);

    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "API error");
    }

    addLog(`DONE ${endpoint}`);
    return data;
  }

  async function chooseFolder(target: "raw" | "output") {
    try {
      const title =
        target === "raw" ? "เลือกโฟลเดอร์ raw FITS" : "เลือกโฟลเดอร์ output";

      const currentPath = target === "raw" ? rawPath : outputPath;

      addLog(`OPEN FOLDER DIALOG: ${title}`);

      const res = await fetch(`${API_BASE}/choose-folder`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title,
          initial_dir: currentPath || null,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Folder dialog error");
      }

      if (!data.path) {
        addLog("Folder selection cancelled.");
        return;
      }

      if (target === "raw") {
        setRawPath(data.path);
        addLog(`Raw folder selected: ${data.path}`);
      } else {
        setOutputPath(data.path);
        setImagePath(`${data.path}/photometry/lightcurve_academic.png`);
        setFitsPreviewPath("");
        addLog(`Output folder selected: ${data.path}`);
      }
    } catch (err) {
      if (err instanceof Error) {
        addLog(`ERROR: ${err.message}`);
      } else {
        addLog("ERROR: Unknown folder selection error");
      }
    }
  }

  function getRunSteps() {
    const endIndex = pipelineSteps.findIndex((s) => s.key === runUntil);
    return pipelineSteps.slice(0, endIndex + 1);
  }

  async function runPipeline() {
    if (!requireRawPath()) return;
    if (!requireOutputPath()) return;

    const x = Number(xStar);
    const y = Number(yStar);

    if (
      getRunSteps().some((step) => step.key === "alignment") &&
      (!Number.isFinite(x) || !Number.isFinite(y))
    ) {
      addLog("ERROR: Please enter reference star x_star and y_star first.");
      setActiveTab("stars");
      return;
    }

    if (getRunSteps().some((step) => step.key === "photometry")) {
      const positions = parseStarPositions();
      if (!positions) {
        setActiveTab("stars");
        return;
      }
    }

    setDoneSteps([]);

    try {
      const selectedSteps = getRunSteps();

      for (const step of selectedSteps) {
        setActiveStep(step.key);

        if (step.key === "headers") {
          await callApi("/read-headers", {
            raw_path: rawPath,
          });
        }

        if (step.key === "calibration") {
          await callApi("/run-calibration", {
            raw_path: rawPath,
            output_path: outputPath,
            skip_existing: true,
            combine_method: "mean",
          });
        }

        if (step.key === "trim") {
          await callApi("/run-trim", {
            input_path: `${outputPath}/calibrated`,
            output_path: `${outputPath}/trimmed`,
            target_width: null,
            target_height: null,
            use_common_min_size: true,
            skip_existing: true,
          });
        }

        if (step.key === "cosmic") {
          await callApi("/run-cosmic-ray", {
            input_path: `${outputPath}/trimmed`,
            output_path: `${outputPath}/cosmic_cleaned`,
            tile_size: 512,
            sigclip: 4.5,
            sigfrac: 0.3,
            objlim: 5.0,
            skip_existing: true,
          });
        }

        if (step.key === "alignment") {
          await callApi("/run-alignment", {
            input_path: `${outputPath}/cosmic_cleaned`,
            output_path: `${outputPath}/aligned`,
            x_star: x,
            y_star: y,
            box_size: 50,
            skip_existing: true,
          });
        }

        if (step.key === "photometry") {
          const positions = parseStarPositions();

          if (!positions) {
            throw new Error("Invalid star positions.");
          }

          await callApi("/run-photometry", {
            input_path: `${outputPath}/aligned`,
            output_csv: `${outputPath}/photometry/photometry_results.csv`,
            positions,
            aperture_radius: null,
            annulus_inner: null,
            annulus_outer: null,
            centroid_box_size: null,
            recenter: true,
            auto_params: true,
          });
        }

        if (step.key === "lightcurve") {
          await plotOnly(false);
        }

        setDoneSteps((prev) => [...new Set([...prev, step.key])]);
      }

      setActiveStep("");
      addLog("Pipeline finished.");
    } catch (err) {
      setActiveStep("");

      if (err instanceof Error) {
        addLog(`ERROR: ${err.message}`);
      } else {
        addLog("ERROR: Unknown error");
      }
    }
  }

  async function plotOnly(writeDoneLog = true) {
    if (!requireOutputPath()) return;

    try {
      setActiveStep("lightcurve");

      const outputPng =
        plotStyle === "1"
          ? `${outputPath}/photometry/lightcurve_academic.png`
          : `${outputPath}/photometry/lightcurve_line.png`;

      await callApi("/plot-lightcurve", {
        photometry_csv: `${outputPath}/photometry/photometry_results.csv`,
        output_png: outputPng,
        show: false,
        remove_first_point: true,
        remove_outliers: true,
        sigma_clip: null,
        bin_size: null,
        mid_transit_jd: null,
        transit_duration_hours: null,
        use_wasp12b_preset: usePreset,
        plot_style: plotStyle,
        title: graphTitle,
      });

      setImagePath(outputPng);
      setPreviewMode("plot");
      setPreviewVersion((v) => v + 1);
      setDoneSteps((prev) => [...new Set([...prev, "lightcurve"])]);
      setActiveStep("");

      if (writeDoneLog) {
        addLog("Plot only finished.");
      }
    } catch (err) {
      setActiveStep("");

      if (err instanceof Error) {
        addLog(`ERROR: ${err.message}`);
      } else {
        addLog("ERROR: Unknown error");
      }
    }
  }

  async function runHeadersOnly() {
    if (!requireRawPath()) return;

    try {
      setActiveStep("headers");

      await callApi("/read-headers", {
        raw_path: rawPath,
      });

      setDoneSteps((prev) => [...new Set([...prev, "headers"])]);
      setActiveStep("");
    } catch (err) {
      setActiveStep("");

      if (err instanceof Error) {
        addLog(`ERROR: ${err.message}`);
      }
    }
  }

  async function runCalibrationOnly() {
    if (!requireRawPath()) return;
    if (!requireOutputPath()) return;

    try {
      setActiveStep("calibration");

      await callApi("/run-calibration", {
        raw_path: rawPath,
        output_path: outputPath,
        skip_existing: true,
        combine_method: "mean",
      });

      setDoneSteps((prev) => [...new Set([...prev, "calibration"])]);
      setActiveStep("");
    } catch (err) {
      setActiveStep("");

      if (err instanceof Error) {
        addLog(`ERROR: ${err.message}`);
      }
    }
  }

  async function runTrimOnly() {
    if (!requireOutputPath()) return;

    try {
      setActiveStep("trim");

      await callApi("/run-trim", {
        input_path: `${outputPath}/calibrated`,
        output_path: `${outputPath}/trimmed`,
        target_width: null,
        target_height: null,
        use_common_min_size: true,
        skip_existing: true,
      });

      setDoneSteps((prev) => [...new Set([...prev, "trim"])]);
      setActiveStep("");
    } catch (err) {
      setActiveStep("");

      if (err instanceof Error) {
        addLog(`ERROR: ${err.message}`);
      }
    }
  }

  async function runCosmicOnly() {
    if (!requireOutputPath()) return;

    try {
      setActiveStep("cosmic");

      await callApi("/run-cosmic-ray", {
        input_path: `${outputPath}/trimmed`,
        output_path: `${outputPath}/cosmic_cleaned`,
        tile_size: 512,
        sigclip: 4.5,
        sigfrac: 0.3,
        objlim: 5.0,
        skip_existing: true,
      });

      setDoneSteps((prev) => [...new Set([...prev, "cosmic"])]);
      setActiveStep("");
    } catch (err) {
      setActiveStep("");

      if (err instanceof Error) {
        addLog(`ERROR: ${err.message}`);
      }
    }
  }

  async function runAlignmentOnly() {
    if (!requireOutputPath()) return;

    const x = Number(xStar);
    const y = Number(yStar);

    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      addLog("ERROR: Please select or enter reference star position first.");
      setActiveTab("stars");
      return;
    }

    try {
      setActiveStep("alignment");

      await callApi("/run-alignment", {
        input_path: `${outputPath}/cosmic_cleaned`,
        output_path: `${outputPath}/aligned`,
        x_star: x,
        y_star: y,
        box_size: 50,
        skip_existing: true,
      });

      setDoneSteps((prev) => [...new Set([...prev, "alignment"])]);
      setActiveStep("");
    } catch (err) {
      setActiveStep("");

      if (err instanceof Error) {
        addLog(`ERROR: ${err.message}`);
      }
    }
  }

  async function runPhotometryOnly() {
    if (!requireOutputPath()) return;

    const positions = parseStarPositions();

    if (!positions) {
      setActiveTab("stars");
      return;
    }

    try {
      setActiveStep("photometry");

      await callApi("/run-photometry", {
        input_path: `${outputPath}/aligned`,
        output_csv: `${outputPath}/photometry/photometry_results.csv`,
        positions,
        aperture_radius: null,
        annulus_inner: null,
        annulus_outer: null,
        centroid_box_size: null,
        recenter: true,
        auto_params: true,
      });

      setDoneSteps((prev) => [...new Set([...prev, "photometry"])]);
      setActiveStep("");
    } catch (err) {
      setActiveStep("");

      if (err instanceof Error) {
        addLog(`ERROR: ${err.message}`);
      }
    }
  }

  function handleTopMenuClick(menu: TopMenuKey) {
    if (menu === "file") {
      setActiveTab("import");
      setViewerMessage("File menu: choose raw FITS folder.");
      addLog("Menu selected: File / Import");
      chooseFolder("raw");
      return;
    }

    if (menu === "edit") {
      setViewerMessage("Edit menu selected. Use fields in the control panel.");
      addLog("Menu selected: Edit");
      return;
    }

    if (menu === "image") {
      setActiveTab("stars");
      setPreviewMode("fits");
      setViewerMessage("Image menu: FITS preview / star selection.");
      addLog("Menu selected: Image");
      return;
    }

    if (menu === "process") {
      setActiveTab("processing");
      setViewerMessage("Process menu: trim, cosmic ray removal, alignment.");
      addLog("Menu selected: Process");
      return;
    }

    if (menu === "analyze") {
      setActiveTab("photometry");
      setViewerMessage("Analyze menu: photometry tools.");
      addLog("Menu selected: Analyze / Photometry");
      return;
    }

    if (menu === "plugins") {
      setActiveTab("calibration");
      setViewerMessage("Plugins menu: calibration pipeline.");
      addLog("Menu selected: Plugins / Calibration");
      return;
    }

    if (menu === "window") {
      setActiveTab("results");
      setViewerMessage("Window menu: results and logs.");
      addLog("Menu selected: Window / Results");
      return;
    }

    if (menu === "help") {
      setActiveTab("results");
      setViewerMessage("Help opened in log panel.");
      addLog(
        "Help: 1) File เลือก raw folder 2) Browse output folder 3) Read Headers 4) Run pipeline"
      );
    }
  }

  function handleToolClick(tool: ToolKey) {
    setActiveTool(tool);

    if (tool === "rectangle") {
      setViewerMessage(
        "Rectangle tool selected. Drag selection will be added later."
      );
      addLog("Tool selected: Rectangle");
    }

    if (tool === "oval") {
      setViewerMessage(
        "Oval aperture tool selected. Aperture overlay will be added later."
      );
      addLog("Tool selected: Oval / Aperture");
    }

    if (tool === "line") {
      setViewerMessage(
        "Line profile tool selected. Line measurement will be added later."
      );
      addLog("Tool selected: Line");
    }

    if (tool === "angle") {
      setViewerMessage(
        "Angle tool selected. Angle measurement will be added later."
      );
      addLog("Tool selected: Angle");
    }

    if (tool === "move") {
      setClickMode(null);
      setViewerMessage("Move tool selected.");
      addLog("Tool selected: Move");
    }

    if (tool === "text") {
      setViewerMessage("Text annotation tool selected.");
      addLog("Tool selected: Text");
    }

    if (tool === "zoom") {
      setZoomLevel((z) => {
        const nextZoom = z >= 2 ? 1 : z + 0.25;
        addLog(`Zoom changed to ${nextZoom.toFixed(2)}x`);
        return nextZoom;
      });

      setViewerMessage("Zoom tool selected. Click again to increase zoom.");
    }

    if (tool === "pan") {
      setViewerMessage("Pan tool selected. Drag pan will be added later.");
      addLog("Tool selected: Pan");
    }

    if (tool === "target") {
      setActiveTab("stars");
      setPreviewMode("fits");
      setClickMode("target");
      setViewerMessage(
        "Target selection mode: click on the viewer to set target coordinates."
      );
      addLog("Tool selected: Target star");
    }

    if (tool === "comparison") {
      setActiveTab("stars");
      setPreviewMode("fits");
      setClickMode("comparison");
      setViewerMessage(
        "Comparison selection mode: click on the viewer to add comparison star."
      );
      addLog("Tool selected: Comparison star");
    }

    if (tool === "aperture") {
      setActiveTab("photometry");
      setViewerMessage(
        "Aperture settings opened. Current mode uses auto FWHM aperture."
      );
      addLog("Tool selected: Aperture settings");
    }

    if (tool === "plot") {
      setActiveTab("lightcurve");
      setPreviewMode("plot");
      setViewerMessage("Light curve tab opened.");
      addLog("Tool selected: Plot light curve");
    }

    if (tool === "run") {
      setViewerMessage("Running selected pipeline steps.");
      addLog("Tool selected: Run pipeline");
      runPipeline();
    }
  }

  function convertViewerClickToFitsCoordinate(
    event: MouseEvent<HTMLDivElement>
  ) {
    const img = viewerImageRef.current;

    if (!img) {
      return null;
    }

    const rect = img.getBoundingClientRect();

    const clickX = event.clientX - rect.left;
    const clickY = event.clientY - rect.top;

    if (
      clickX < 0 ||
      clickY < 0 ||
      clickX > rect.width ||
      clickY > rect.height
    ) {
      return null;
    }

    if (previewMode === "fits") {
      const displayX = clickX / zoomLevel;
      const displayY = clickY / zoomLevel;

      const previewX = displayX * fitsDownsample;
      const previewY = (rect.height / zoomLevel - displayY) * fitsDownsample;

      return {
        x: Number(previewX.toFixed(2)),
        y: Number(previewY.toFixed(2)),
      };
    }

    return {
      x: Number(clickX.toFixed(2)),
      y: Number(clickY.toFixed(2)),
    };
  }

  function handleViewerClick(event: MouseEvent<HTMLDivElement>) {
    const point = convertViewerClickToFitsCoordinate(event);

    if (!point) {
      return;
    }

    const roundedX = point.x;
    const roundedY = point.y;

    if (activeTool === "zoom") {
      setZoomLevel((z) => {
        const nextZoom = z >= 2 ? 1 : z + 0.25;
        addLog(`Viewer zoom changed to ${nextZoom.toFixed(2)}x`);
        return nextZoom;
      });
      return;
    }

    if (clickMode === "target") {
      setXStar(String(roundedX));
      setYStar(String(roundedY));

      try {
        const positions = JSON.parse(positionsText);

        if (Array.isArray(positions)) {
          positions[0] = [roundedX, roundedY];
          setPositionsText(JSON.stringify(positions, null, 2));
        }
      } catch {
        setPositionsText(JSON.stringify([[roundedX, roundedY]], null, 2));
      }

      addLog(`Target selected at x=${roundedX}, y=${roundedY}`);
      setViewerMessage(`Target selected: x=${roundedX}, y=${roundedY}`);
      return;
    }

    if (clickMode === "comparison") {
      try {
        const positions = JSON.parse(positionsText);

        if (Array.isArray(positions)) {
          positions.push([roundedX, roundedY]);
          setPositionsText(JSON.stringify(positions, null, 2));
        }
      } catch {
        setPositionsText(
          JSON.stringify(
            [
              [0, 0],
              [roundedX, roundedY],
            ],
            null,
            2
          )
        );
      }

      addLog(`Comparison star added at x=${roundedX}, y=${roundedY}`);
      setViewerMessage(`Comparison star added: x=${roundedX}, y=${roundedY}`);
      return;
    }

    addLog(
      `Viewer clicked at x=${roundedX}, y=${roundedY} with tool ${activeTool}`
    );
    setViewerMessage(
      `Clicked x=${roundedX}, y=${roundedY} using ${activeTool} tool`
    );
  }

  return (
    <main className="flex min-h-screen flex-col bg-[#d8d8d8] text-slate-900">
      <header className="border-b border-slate-400 bg-[#eeeeee]">
        <div className="flex h-7 items-center gap-5 px-2 text-sm">
          {topMenuButtons.map((menu) => (
            <button
              key={menu.key}
              onClick={() => handleTopMenuClick(menu.key)}
              className="hover:underline"
            >
              {menu.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-[2px] border-t border-slate-300 bg-[#eeeeee] px-1 py-1">
          {toolbarButtons.map((tool) => (
            <button
              key={tool.key}
              title={tool.title}
              className={`flex h-8 w-8 items-center justify-center border text-sm font-semibold shadow-sm hover:bg-white ${
                activeTool === tool.key
                  ? "border-blue-700 bg-blue-100 text-blue-800"
                  : "border-slate-500 bg-slate-100 text-slate-900"
              }`}
              onClick={() => handleToolClick(tool.key)}
            >
              {tool.label}
            </button>
          ))}
        </div>
      </header>

      <section className="border-b border-slate-400 bg-[#f7f7f7] px-3 py-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold">AstroPipeline</h1>
            <p className="text-xs text-slate-600">
              FITS calibration · photometry · light curve · transit analysis
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="rounded bg-slate-200 px-2 py-1">
              API: {API_BASE}
            </span>
            <span className="rounded bg-slate-200 px-2 py-1">
              Active: {activeStep || "Idle"}
            </span>
          </div>
        </div>
      </section>

      <nav className="border-b border-slate-400 bg-[#e8e8e8] px-2 pt-2">
        <div className="flex flex-wrap gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`rounded-t-lg border border-b-0 px-4 py-2 text-sm font-medium ${
                activeTab === tab.key
                  ? "border-slate-500 bg-white text-slate-900"
                  : "border-slate-400 bg-slate-200 text-slate-600 hover:bg-slate-100"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <div className="grid flex-1 grid-cols-1 gap-3 p-3 lg:grid-cols-[1fr_360px]">
        <section className="flex min-h-[620px] flex-col border border-slate-500 bg-white">
          <div className="flex items-center justify-between border-b border-slate-300 bg-[#f5f5f5] px-3 py-2">
            <div>
              <h2 className="font-semibold">Image / Plot Viewer</h2>
              <p className="text-xs text-slate-500">
                Preview graph or FITS image stack
              </p>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setPreviewVersion((v) => v + 1)}
                className="border border-slate-500 bg-slate-100 px-3 py-1 text-xs hover:bg-white"
              >
                Refresh
              </button>

              <button
                onClick={() => setActiveTab("results")}
                className="border border-slate-500 bg-slate-100 px-3 py-1 text-xs hover:bg-white"
              >
                Results
              </button>
            </div>
          </div>

          <div
            onClick={handleViewerClick}
            className={`relative flex flex-1 items-center justify-center overflow-hidden bg-[#fbfbfb] p-3 ${
              activeTool === "target" || activeTool === "comparison"
                ? "cursor-crosshair"
                : activeTool === "zoom"
                ? "cursor-zoom-in"
                : activeTool === "pan"
                ? "cursor-grab"
                : "cursor-default"
            }`}
          >
            {imageUrl ? (
              <img
                ref={viewerImageRef}
                src={imageUrl}
                alt={previewMode === "fits" ? "FITS preview" : "Light curve"}
                className="max-h-[560px] max-w-full object-contain transition-transform"
                style={{
                  transform: `scale(${zoomLevel})`,
                }}
              />
            ) : (
              <p className="text-slate-400">No image selected</p>
            )}

            <div className="absolute bottom-3 left-3 rounded bg-white/90 px-3 py-1 text-xs text-slate-700 shadow">
              Tool: {activeTool} | Zoom: {zoomLevel.toFixed(2)}x
            </div>

            <div className="absolute bottom-3 right-3 rounded bg-white/90 px-3 py-1 text-xs text-slate-700 shadow">
              {viewerMessage}
            </div>
          </div>

          <div className="border-t border-slate-300 bg-[#f5f5f5] px-3 py-2 text-xs text-slate-600">
            Preview path: {previewMode === "fits" ? fitsPreviewPath : imagePath}
          </div>
        </section>

        <aside className="min-h-[620px] border border-slate-500 bg-white">
          <div className="border-b border-slate-300 bg-[#f5f5f5] px-3 py-2">
            <h2 className="font-semibold">Control Panel</h2>
            <p className="text-xs text-slate-500">{activeTab}</p>
          </div>

          <div className="max-h-[760px] overflow-auto p-4">
            {activeTab === "import" && (
              <div className="space-y-4">
                <h3 className="text-lg font-bold">Import FITS</h3>

                <div className="space-y-2">
                  <label className="block">
                    <span className="text-sm font-medium">Raw folder path</span>
                    <input
                      value={rawPath}
                      onChange={(e) => setRawPath(e.target.value)}
                      placeholder="Select raw FITS folder..."
                      className="mt-1 w-full border border-slate-400 px-2 py-1 text-sm"
                    />
                  </label>

                  <button
                    onClick={() => chooseFolder("raw")}
                    className="w-full border border-slate-600 bg-slate-100 px-3 py-2 text-sm font-semibold hover:bg-white"
                  >
                    Browse Raw Folder
                  </button>
                </div>

                <div className="space-y-2">
                  <label className="block">
                    <span className="text-sm font-medium">Output folder path</span>
                    <input
                      value={outputPath}
                      onChange={(e) => setOutputPath(e.target.value)}
                      placeholder="Select output folder..."
                      className="mt-1 w-full border border-slate-400 px-2 py-1 text-sm"
                    />
                  </label>

                  <button
                    onClick={() => chooseFolder("output")}
                    className="w-full border border-slate-600 bg-slate-100 px-3 py-2 text-sm font-semibold hover:bg-white"
                  >
                    Browse Output Folder
                  </button>
                </div>

                <button
                  onClick={runHeadersOnly}
                  className="w-full border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  Read Headers
                </button>
              </div>
            )}

            {activeTab === "calibration" && (
              <div className="space-y-4">
                <h3 className="text-lg font-bold">Calibration</h3>
                <p className="text-sm text-slate-500">
                  Create master bias, dark, flat and calibrated light frames.
                </p>

                <button
                  onClick={runCalibrationOnly}
                  className="w-full border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  Run Calibration
                </button>
              </div>
            )}

            {activeTab === "processing" && (
              <div className="space-y-4">
                <h3 className="text-lg font-bold">Image Processing</h3>

                <button
                  onClick={runTrimOnly}
                  className="w-full border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  Run Trim
                </button>

                <button
                  onClick={runCosmicOnly}
                  className="w-full border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  Cosmic Ray Removal
                </button>

                <button
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
                  onClick={runPhotometryOnly}
                  className="w-full border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  Run Photometry
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
                onClick={runPipeline}
                className="mt-3 w-full border border-red-800 bg-red-700 px-3 py-2 text-sm font-semibold text-white hover:bg-red-600"
              >
                Run Pipeline
              </button>
            </div>
          </div>
        </aside>
      </div>

      <footer className="border-t border-slate-500 bg-[#eeeeee] px-3 py-2 text-xs">
        <div className="flex flex-wrap items-center gap-4">
          <span>Status: {activeStep || "Ready"}</span>
          <span>Tool: {activeTool}</span>
          <span>Zoom: {zoomLevel.toFixed(2)}x</span>
          <span>Done: {doneSteps.length} step(s)</span>
          <span>Raw: {rawPath || "not selected"}</span>
          <span>Output: {outputPath || "not selected"}</span>
        </div>
      </footer>
    </main>
  );
}