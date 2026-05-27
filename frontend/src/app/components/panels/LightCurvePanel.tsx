type LightCurvePanelProps = {
  imagePath: string;
  setImagePath: (value: string) => void;
  runPlotLightCurve: () => void;
};

export function LightCurvePanel({
  imagePath,
  setImagePath,
  runPlotLightCurve,
}: LightCurvePanelProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold">Light Curve</h3>

      <p className="text-sm text-slate-500">
        Generate and preview the final light curve plot.
      </p>

      <label className="block">
        <span className="text-sm font-medium">Light curve image path</span>

        <input
          value={imagePath}
          onChange={(e) => setImagePath(e.target.value)}
          placeholder="output/lightcurve.png"
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>

      <button
        type="button"
        onClick={runPlotLightCurve}
        className="w-full rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
      >
        Plot Light Curve
      </button>
    </div>
  );
}