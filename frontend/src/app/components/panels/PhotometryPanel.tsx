type PhotometryPanelProps = {
  positionsText: string;
  setPositionsText: (value: string) => void;
  runPhotometryOnly: () => void;
};

export function PhotometryPanel({
  positionsText,
  setPositionsText,
  runPhotometryOnly,
}: PhotometryPanelProps) {

  const hasPositions = (() => {
    try {
      const positions = JSON.parse(positionsText);
      return Array.isArray(positions) && positions.length > 1;
    } catch {
      return false;
    }
  })();

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold">Photometry</h3>

      <p className="text-sm text-slate-500">
        Run aperture photometry using the selected target and comparison stars.
      </p>

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

      <button
        type="button"
        onClick={runPhotometryOnly}
        disabled={!hasPositions}
        className={`w-full rounded-lg px-3 py-2 text-sm font-semibold text-white ${
          hasPositions
            ? "bg-slate-900 hover:bg-slate-700"
            : "cursor-not-allowed bg-slate-400"
        }`}
      >
        Run Photometry
      </button>
    </div>
  );
}