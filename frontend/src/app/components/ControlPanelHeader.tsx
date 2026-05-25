import type { TabKey } from "../types/pipeline";

type ControlPanelHeaderProps = {
  activeTab: TabKey;
  onPreview: () => void;
};

export function ControlPanelHeader({
  activeTab,
  onPreview,
}: ControlPanelHeaderProps) {
  return (
    <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">
      <div>
        <h2 className="font-semibold">Control Panel</h2>
        <p className="text-xs text-slate-500">{activeTab}</p>
      </div>

      <button
        type="button"
        onClick={onPreview}
        className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-100"
      >
        Preview
      </button>
    </div>
  );
}