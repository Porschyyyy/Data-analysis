import type { PipelineStep, TabItem, ToolbarButton } from "../types/pipeline";
import type { ToolKey } from "../types/pipeline";
import {
  Aperture,
  Crosshair,
  ImagePlus,
  Move,
  Play,
  ScanSearch,
  Stars,
  ZoomIn,
} from "lucide-react";



export const API_BASE = "http://127.0.0.1:8000";

export const pipelineSteps: PipelineStep[] = [
  { key: "headers", label: "Import / Headers" },
  { key: "calibration", label: "Master + Calibrated" },
  { key: "trim", label: "Trim" },
  { key: "cosmic", label: "Cosmic Ray" },
  { key: "alignment", label: "Alignment" },
  { key: "photometry", label: "Photometry" },
  { key: "lightcurve", label: "Light Curve" },
];

export const tabs: TabItem[] = [
  { key: "import", label: "Import" },
  { key: "calibration", label: "Calibration" },
  { key: "processing", label: "Image Processing" },
  { key: "stars", label: "Star Selection" },
  { key: "photometry", label: "Photometry" },
  { key: "lightcurve", label: "Light Curve" },
];

export const toolbarButtons: ToolbarButton[] = [
  {
    key: "move",
    title: "Move / Pan image",
    icon: Move,
  },
  {
    key: "zoom",
    title: "Zoom image",
    icon: ZoomIn,
  },
  {
    key: "fit",
    title: "Fit image / reset zoom",
    icon: ImagePlus,
  },
  {
    key: "pick",
    title: "Pick reference star",
    icon: Crosshair,
  },
  {
    key: "target",
    title: "Select target star",
    icon: Stars,
  },
  {
    key: "comparison",
    title: "Select comparison star",
    icon: Aperture,
  },
  {
    key: "photometry",
    title: "Run photometry",
    icon: ScanSearch,
  },
  {
    key: "run",
    title: "Run pipeline",
    icon: Play,
  },
];

export const defaultPositionsText = `[
  [1110.28, 868.72],
  [1286.90, 2525.87],
  [2918.07, 3066.12]
]`;
