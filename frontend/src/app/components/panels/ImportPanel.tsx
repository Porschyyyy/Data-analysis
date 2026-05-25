type ImportPanelProps = {
  rawPath: string;
  outputPath: string;
  setRawPath: (value: string) => void;
  setOutputPath: (value: string) => void;
  chooseRawFolder: () => void;
  chooseOutputFolder: () => void;
  runHeadersOnly: () => void;
};

export function ImportPanel({
  rawPath,
  outputPath,
  setRawPath,
  setOutputPath,
  chooseRawFolder,
  chooseOutputFolder,
  runHeadersOnly,
}: ImportPanelProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold">Import FITS</h3>

      <label className="block">
        <span className="text-sm font-medium">Raw folder path</span>
        <input
          value={rawPath}
          onChange={(e) => setRawPath(e.target.value)}
          placeholder="Select raw FITS folder..."
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>

      <button
        type="button"
        onClick={chooseRawFolder}
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold hover:bg-slate-100"
      >
        Browse Raw Folder
      </button>

      <label className="block">
        <span className="text-sm font-medium">Output folder path</span>
        <input
          value={outputPath}
          onChange={(e) => setOutputPath(e.target.value)}
          placeholder="Select output folder..."
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>

      <button
        type="button"
        onClick={chooseOutputFolder}
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold hover:bg-slate-100"
      >
        Browse Output Folder
      </button>

      <button
        type="button"
        onClick={runHeadersOnly}
        className="w-full rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
      >
        Read Headers
      </button>
    </div>
  );
}