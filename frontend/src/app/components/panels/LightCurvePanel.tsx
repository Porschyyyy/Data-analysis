type LightCurvePanelProps = {
  imagePath: string;
  setImagePath: (value: string) => void;
  runPlotLightCurve: () => void;
  modelType: "data_only" | "transit";
  setModelType: (value: "data_only" | "transit") => void;
};

export function LightCurvePanel({
  imagePath,
  setImagePath,
  runPlotLightCurve,
  modelType,
  setModelType,
}: LightCurvePanelProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold">Light Curve</h3>

      <p className="text-sm text-slate-500">
        Generate a light curve plot or fit a transit model using the photometry results.
      </p>

      <label className="block">
        <span className="text-sm font-medium">Output image</span>

        <input
          value={imagePath}
          onChange={(e) => setImagePath(e.target.value)}
          placeholder="Generated automatically"
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>

      <button
        type="button"
        onClick={() => {
          setModelType("data_only");
          runPlotLightCurve();
        }}
          className="w-full rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
        >
          Plot Light Curve
        </button>

        <hr className="my-4" />

        <h4 className="font-semibold">
          Model Fitting
        </h4>

        <label className="block">
          <span className="text-sm font-medium">Model type</span>

          <select
            value={modelType}
            onChange={(e) =>
              setModelType(e.target.value as "transit")
            }
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            <option value="transit">Exoplanet Transit</option>
          </select>
        </label>

        <button
          type="button"
          onClick={() => {
            setModelType("transit");
            runPlotLightCurve();
          }}
          className="w-full rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
        >
          Fit Model
        </button>
    </div>
  );
}