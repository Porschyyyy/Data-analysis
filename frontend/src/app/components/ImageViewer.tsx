import type { RefObject } from "react";
import type { PreviewMode, ToolKey, ViewerClickEvent } from "../types/pipeline";

type ImageViewerProps = {
  viewerImageRef: RefObject<HTMLImageElement | null>;
  previewMode: PreviewMode;
  activeTool: ToolKey;
  previewUrl: string;
  imagePath: string;
  fitsPreviewPath: string;
  viewerMessage: string;
  zoomLevel: number;
  onViewerClick: (event: ViewerClickEvent) => void;
  onRefresh: () => void;
  onResults: () => void;
};

export function ImageViewer({
  viewerImageRef,
  previewMode,
  activeTool,
  previewUrl,
  imagePath,
  fitsPreviewPath,
  viewerMessage,
  zoomLevel,
  onViewerClick,
  onRefresh,
  onResults,
}: ImageViewerProps) {
  const hasPreview = previewMode === "fits" ? Boolean(fitsPreviewPath) : Boolean(imagePath);

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">
        <div>
          <h2 className="font-semibold">Image / Plot Viewer</h2>
          <p className="text-xs text-slate-500">Preview graph or FITS image stack</p>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={onRefresh}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-xs font-semibold hover:bg-slate-100"
          >
            Refresh
          </button>

          <button
            type="button"
            onClick={onResults}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-xs font-semibold hover:bg-slate-100"
          >
            Results
          </button>
        </div>
      </div>

      <div
        onClick={onViewerClick}
        className={`relative flex min-h-155 items-center justify-center overflow-hidden bg-slate-100 p-4 ${
          activeTool === "target" || activeTool === "comparison"
            ? "cursor-crosshair"
            : activeTool === "zoom"
            ? "cursor-zoom-in"
            : activeTool === "move"
            ? "cursor-grab"
            : "cursor-default"
        }`}
      >
        {hasPreview ? (
          <img
            ref={viewerImageRef}
            src={previewUrl}
            alt={previewMode === "fits" ? "FITS preview" : "Plot preview"}
            style={{
              transform: `scale(${zoomLevel})`,
              transformOrigin: "center",
            }}
            className="max-h-150 max-w-full rounded-lg shadow"
          />
        ) : (
          <p className="text-sm text-slate-400">No image selected</p>
        )}

        <div className="absolute bottom-3 left-3 rounded-lg bg-white/90 px-3 py-1 text-xs shadow">
          Tool: {activeTool} | Zoom: {zoomLevel.toFixed(2)}x
        </div>

        <div className="absolute bottom-3 right-3 rounded-lg bg-white/90 px-3 py-1 text-xs shadow">
          {viewerMessage}
        </div>
      </div>

      <div className="border-t border-slate-200 bg-white px-4 py-2 text-xs text-slate-500">
        Preview path: {previewMode === "fits" ? fitsPreviewPath : imagePath}
      </div>
    </section>
  );
}