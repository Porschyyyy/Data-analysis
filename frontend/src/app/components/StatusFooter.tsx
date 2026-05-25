import type { ToolKey } from "../types/pipeline";

type StatusFooterProps = {
  currentImageIndex: number;
  totalImages: number;
  processingMessage: string;
  isBackendRunning: boolean;
  activeTool: ToolKey;
  zoomLevel: number;
  rawPath: string;
  outputPath: string;
  doneStepsLength: number;
};

export function StatusFooter({
  currentImageIndex,
  totalImages,
  processingMessage,
  isBackendRunning,
  activeTool,
  zoomLevel,
  rawPath,
  outputPath,
  doneStepsLength,
}: StatusFooterProps) {
  const progressPercent =
    totalImages > 0
      ? Math.min(100, Math.round((currentImageIndex / totalImages) * 100))
      : 0;

  const statusLabel = isBackendRunning ? "Processing" : "Ready";
  const rawLabel = rawPath ? "Selected" : "None";
  const outputLabel = outputPath ? "Selected" : "None";

  return (
    <footer className="border-t border-slate-200 bg-white/90 px-4 py-3 shadow-[0_-8px_30px_rgba(15,23,42,0.08)]">
      <div className="flex flex-wrap items-center gap-4 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div>
          <p className="text-xs text-slate-500">Status</p>
          <p
            className={`text-sm font-bold ${
              isBackendRunning ? "text-blue-600" : "text-emerald-600"
            }`}
          >
            {statusLabel}
          </p>
        </div>

        <div className="min-w-72 flex-1">
          <div className="mb-1 flex items-center justify-between">
            <p className="text-xs text-slate-500">Progress</p>
            <p className="text-sm font-bold text-blue-600">
              {totalImages > 0
                ? `${currentImageIndex} / ${totalImages} images`
                : "No active task"}
            </p>
          </div>

          <div className="h-2 overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-blue-600 transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          <p className="mt-1 text-xs text-slate-500">{processingMessage}</p>
        </div>

        <div>
          <p className="text-xs text-slate-500">Tool</p>
          <p className="text-sm font-semibold text-slate-800">{activeTool}</p>
        </div>

        <div>
          <p className="text-xs text-slate-500">Zoom</p>
          <p className="text-sm font-semibold text-slate-800">
            {(zoomLevel * 100).toFixed(0)}%
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-500">Raw</p>
          <p className="text-sm font-semibold text-slate-800">{rawLabel}</p>
        </div>

        <div>
          <p className="text-xs text-slate-500">Output</p>
          <p className="text-sm font-semibold text-slate-800">{outputLabel}</p>
        </div>

        <div>
          <p className="text-xs text-slate-500">Done</p>
          <p className="text-sm font-semibold text-slate-800">
            {doneStepsLength} step(s)
          </p>
        </div>
      </div>
    </footer>
  );
}