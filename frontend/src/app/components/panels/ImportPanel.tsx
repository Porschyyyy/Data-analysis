type ImportPanelProps = {
  rawPath: string;
  outputPath: string;
  setRawPath: (value: string) => void;
  setOutputPath: (value: string) => void;
  runHeadersOnly: () => void;
  uploadFolder: (files: FileList | null) => Promise<void>;
  isUploading: boolean;
};

export function ImportPanel({
  rawPath,
  outputPath,
  setRawPath,
  setOutputPath,
  runHeadersOnly,
  uploadFolder,
  isUploading,
}: ImportPanelProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold">Import FITS</h3>

      <label className="block rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4">
        <span className="block text-sm font-semibold text-slate-800">
          Upload FITS folder
        </span>
        <span className="mt-1 block text-xs text-slate-500">
          Select a folder containing FITS files. The files will be uploaded to the server.
        </span>

        <input
          type="file"
          multiple
          // @ts-expect-error webkitdirectory is supported by Chromium browsers
          webkitdirectory="true"
          onChange={(e) => uploadFolder(e.target.files)}
          className="mt-3 w-full text-sm"
        />
      </label>

      <label className="block">
        <span className="text-sm font-medium">Raw folder path</span>
        <input
          value={rawPath}
          readOnly
          className="mt-1 w-full rounded-lg border border-slate-300 bg-slate-100 px-3 py-2 text-sm text-slate-600"
        />
      </label>

      <label className="block">
        <span className="text-sm font-medium">Output folder path</span>
        <input
          value={outputPath}
          readOnly
          className="mt-1 w-full rounded-lg border border-slate-300 bg-slate-100 px-3 py-2 text-sm text-slate-600"
        />
      </label>

      <button
        type="button"
        onClick={runHeadersOnly}
        disabled={isUploading}
        className="w-full rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
      >
        {isUploading ? "Uploading..." : "Read Headers"}
      </button>
    </div>
  );
}