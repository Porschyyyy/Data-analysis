import type { ComponentType, MouseEvent } from "react";

export type StepKey =
  | "headers"
  | "calibration"
  | "trim"
  | "cosmic"
  | "alignment"
  | "photometry"
  | "lightcurve";

export type TabKey =
  | "import"
  | "calibration"
  | "processing"
  | "stars"
  | "photometry"
  | "lightcurve"

export type ToolKey =
  | "move"
  | "zoom"
  | "fit"
  | "pick"
  | "target"
  | "comparison"
  | "aperture"
  | "photometry"
  | "plot"
  | "run";


export type PreviewMode = "plot" | "fits";
export type PlotStyle = "academic" | "line";
export type ClickMode = "target" | "comparison" | null;

export type PipelineStep = { key: StepKey; label: string };
export type TabItem = { key: TabKey; label: string };
export type ToolbarButton = {
  key: ToolKey;
  title: string;
  icon: ComponentType<{ size?: number; className?: string }>;
};

export type FitsPoint = { x: number; y: number };

export type AddLog = (message: string) => void;
export type ViewerClickEvent = MouseEvent<HTMLDivElement>;
