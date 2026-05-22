import type { PlotStyle } from "../types/pipeline";

export const headersPayload = (rawPath: string) => ({ raw_path: rawPath });

export const calibrationPayload = (rawPath: string, outputPath: string) => ({
  raw_path: rawPath,
  output_path: outputPath,
  skip_existing: true,
  combine_method: "mean",
});

export const trimPayload = (outputPath: string) => ({
  input_path: `${outputPath}/calibrated`,
  output_path: `${outputPath}/trimmed`,
  target_width: null,
  target_height: null,
  use_common_min_size: true,
  skip_existing: true,
});

export const cosmicPayload = (outputPath: string) => ({
  input_path: `${outputPath}/trimmed`,
  output_path: `${outputPath}/cosmic_cleaned`,
  tile_size: 512,
  sigclip: 4.5,
  sigfrac: 0.3,
  objlim: 5.0,
  skip_existing: true,
});

export const alignmentPayload = (outputPath: string, x: number, y: number) => ({
  input_path: `${outputPath}/cosmic_cleaned`,
  output_path: `${outputPath}/aligned`,
  x_star: x,
  y_star: y,
  box_size: 50,
  skip_existing: true,
});

export const photometryPayload = (outputPath: string, positions: number[][]) => ({
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

export function getOutputPng(outputPath: string, plotStyle: PlotStyle) {
  return plotStyle === "1"
    ? `${outputPath}/photometry/lightcurve_academic.png`
    : `${outputPath}/photometry/lightcurve_line.png`;
}

export const lightcurvePayload = ({
  outputPath,
  outputPng,
  plotStyle,
  graphTitle,
  usePreset,
}: {
  outputPath: string;
  outputPng: string;
  plotStyle: PlotStyle;
  graphTitle: string;
  usePreset: boolean;
}) => ({
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
