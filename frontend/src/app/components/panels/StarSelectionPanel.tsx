type StarSelectionPanelProps = {
  fitsPreviewPath: string;
  setFitsPreviewPath: (value: string) => void;

  fitsFiles: string[];
  fitsDownsample: number;
  setFitsDownsample: (value: number) => void;

  xStar: string;
  yStar: string;
  setXStar: (value: string) => void;
  setYStar: (value: string) => void;

  positionsText: string;
  setPositionsText: (value: string) => void;

  comparisonTargetCount: number;
  setComparisonTargetCount: (value: number) => void;
  comparisonCount: number;

  loadFitsPreview: () => void;

  undoLastMarker: () => void;
  clearComparisonMarkers: () => void;
  clearAllMarkers: () => void;
};

export function StarSelectionPanel({
  fitsPreviewPath,
  setFitsPreviewPath,
  fitsFiles,
  fitsDownsample,
  setFitsDownsample,
  xStar,
  yStar,
  setXStar,
  setYStar,
  positionsText,
  setPositionsText,
  comparisonTargetCount,
  setComparisonTargetCount,
  comparisonCount,
  loadFitsPreview,
  undoLastMarker,
  clearComparisonMarkers,
  clearAllMarkers,
}: StarSelectionPanelProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold">Star Selection</h3>

      <label className="block">
        <span className="text-sm font-medium">FITS preview path</span>

        <input
          value={fitsPreviewPath}
          onChange={(e) => setFitsPreviewPath(e.target.value)}
          placeholder="Preview FITS file path"
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>

      <select
        value={fitsPreviewPath}
        onChange={(e) => setFitsPreviewPath(e.target.value)}
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
      >
        <option value="">Select FITS file...</option>
        {fitsFiles.map((file) => (
          <option key={file} value={file}>
            {file}
          </option>
        ))}
      </select>

      <label className="block">
        <span className="text-sm font-medium">Preview downsample</span>
        <input
          type="number"
          value={fitsDownsample}
          onChange={(e) => setFitsDownsample(Number(e.target.value))}
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>

      <button
        type="button"
        onClick={loadFitsPreview}
        className="w-full rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
      >
        Load FITS Preview
      </button>

      <div className="grid grid-cols-2 gap-3">
        <label>
          <span className="text-sm font-medium">Reference Star X</span>
          <input
            value={xStar}
            onChange={(e) => setXStar(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>

        <label>
          <span className="text-sm font-medium">Reference Star Y</span>
          <input
            value={yStar}
            onChange={(e) => setYStar(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
      </div>

      <label className="block">
        <span className="text-sm font-medium">Comparison stars needed</span>
        <select
          value={comparisonTargetCount}
          onChange={(e) => setComparisonTargetCount(Number(e.target.value))}
          className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
        >
          {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </label>

      <p className="text-xs text-slate-500">
        Selected: {comparisonCount} / {comparisonTargetCount}
      </p>

      <div className="grid grid-cols-1 gap-2">
        <button
            type="button"
            onClick={undoLastMarker}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold hover:bg-slate-100"
        >
            Undo last marker
        </button>

        <button
            type="button"
            onClick={clearComparisonMarkers}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold hover:bg-slate-100"
        >
             Clear comparison markers
        </button>

        <button
            type="button"
            onClick={clearAllMarkers}
            className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-100"
        >
            Clear all markers
        </button>
      </div>

      <label className="block">
        <span className="text-sm font-medium">Photometry positions</span>
        <div className="mt-3 overflow-hidden rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 text-slate-700">
              <tr>
                <th className="px-3 py-2 text-left">Star</th>
                <th className="px-3 py-2 text-left">X</th>
                <th className="px-3 py-2 text-left">Y</th>
              </tr>
            </thead>

            <tbody>
              {(() => {
                try {
                  const positions = JSON.parse(positionsText);

                  return positions.map((pos: number[], index: number) => (
                    <tr
                      key={index}
                      className="border-t border-slate-200"
                    >
                      <td className="px-3 py-2 font-medium">
                        {index === 0
                          ? "Target"
                          : `Comparison ${index}`}
                      </td>

                      <td className="px-3 py-2">
                        {Number(pos[0]).toFixed(2)}
                      </td>

                      <td className="px-3 py-2">
                        {Number(pos[1]).toFixed(2)}
                      </td>
                    </tr>
                  ));
                } catch {
                  return (
                    <tr>
                      <td
                        colSpan={3}
                        className="px-3 py-3 text-center text-slate-400"
                      >
                        No star positions selected
                      </td>
                    </tr>
                  );
                }
              })()}
            </tbody>
          </table>
        </div>
      </label>

      <p className="text-xs text-slate-500">
        The first position is the target star. All remaining positions are comparison stars.
      </p>
    </div>
  );
}