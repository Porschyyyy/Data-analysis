import React from "react";

type TrimSummary = {
  n_files: number;
  size_counts: { width: number; height: number; count: number }[];
  crop_target: { width: number; height: number };
};

type ProcessingPanelProps = {
  imageProcessingPreviewStep: string;
  setImageProcessingPreviewStep: (
    value: "calibrated" | "trimmed" | "cosmic_cleaned" | "aligned"
  ) => void;

  runTrimOnly: () => void;
  runCosmicRayOnly: () => void;
  runAlignmentOnly: () => void;

  xStar: string;
  yStar: string;
  setXStar: (value: string) => void;
  setYStar: (value: string) => void;

  useCommonMinSize: boolean;
  setUseCommonMinSize: (value: boolean) => void;

  trimSummary: TrimSummary | null;
  loadTrimSummary: () => void;

};

export function ProcessingPanel({
  imageProcessingPreviewStep,
  setImageProcessingPreviewStep,

  runTrimOnly,
  runCosmicRayOnly,
  runAlignmentOnly,

  xStar,
  yStar,
  setXStar,
  setYStar,

  useCommonMinSize,
  setUseCommonMinSize,

  trimSummary,
  loadTrimSummary,

}: ProcessingPanelProps) {
  return (
    <div className="space-y-5">
      <h3 className="text-lg font-bold">Image Processing</h3>

      <label className="block">
        <span className="text-sm font-medium">
          Preview processing step
        </span>

        <select
          value={imageProcessingPreviewStep}
          onChange={(e) =>
            setImageProcessingPreviewStep(
              e.target.value as "calibrated" | "trimmed" | "cosmic_cleaned" | "aligned"
            )
          }
          className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
        >
          <option value="trimmed">trimmed</option>
          <option value="cosmic_cleaned">cosmic_cleaned</option>
          <option value="aligned">aligned</option>
        </select>
      </label>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h4 className="font-semibold">Trim</h4>

        <p className="mt-1 text-xs text-slate-500">
          Crop images to common size
        </p>

        <label className="mt-3 flex items-start gap-2 rounded-lg bg-slate-50 p-3 text-sm">
          <input
            type="checkbox"
            checked={useCommonMinSize}
            onChange={(e) => setUseCommonMinSize(e.target.checked)}
            className="mt-1"
          />

          <span>
            <span className="font-medium">Auto crop to common size</span>
            <span className="block text-xs text-slate-500">
              Crop all images to the smallest shared width/height before processing.
              Recommended when image sizes are slightly different.
            </span>
          </span>
        </label>

        <button
          type="button"
          onClick={loadTrimSummary}
          className="mt-3 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold hover:bg-slate-100"
        >
          Check image sizes
        </button>

        {trimSummary && (
          <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
            <p className="font-semibold text-slate-800">Detected image sizes:</p>

            <div className="mt-2 space-y-1">
              {trimSummary.size_counts.map((item) => (
                <p key={`${item.width}x${item.height}`}>
                  {item.width}x{item.height} → {item.count} files
                </p>
              ))}
            </div>

            <p className="mt-3 font-semibold text-slate-800">Crop target:</p>
            <p>
              {trimSummary.crop_target.width}x{trimSummary.crop_target.height}
            </p>
          </div>
        )}

        <button
          type="button"
          onClick={runTrimOnly}
          className="mt-3 w-full rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
        >
          Run Trim
        </button>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h4 className="font-semibold">Cosmic Ray Removal</h4>

        <p className="mt-1 text-xs text-slate-500">
          Remove cosmic ray artifacts
        </p>

        <button
          type="button"
          onClick={runCosmicRayOnly}
          className="mt-3 w-full rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
        >
          Run Cosmic Ray Removal
        </button>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h4 className="font-semibold">Alignment</h4>

        <div className="mt-3 grid grid-cols-2 gap-3">
          <label>
            <span className="text-sm font-medium">x_star</span>

            <input
              value={xStar}
              onChange={(e) => setXStar(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </label>

          <label>
            <span className="text-sm font-medium">y_star</span>

            <input
              value={yStar}
              onChange={(e) => setYStar(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
        </div>

        <button
          type="button"
          onClick={runAlignmentOnly}
          className="mt-4 w-full rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
        >
          Run Alignment
        </button>
      </div>
    </div>
  );
}