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
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold">Photometry</h3>

      <p className="text-sm text-slate-500">
        Run aperture photometry using the selected target and comparison stars.
      </p>

      <label className="block">
        <span className="text-sm font-medium">Photometry positions JSON</span>
        <textarea
          value={positionsText}
          onChange={(e) => setPositionsText(e.target.value)}
          rows={9}
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
        />
      </label>

      <p className="text-xs text-slate-500">
        positions[0] คือ target star และ positions[1:] คือ comparison stars
      </p>

      <button
        type="button"
        onClick={runPhotometryOnly}
        className="w-full rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
      >
        Run Photometry
      </button>
    </div>
  );
}