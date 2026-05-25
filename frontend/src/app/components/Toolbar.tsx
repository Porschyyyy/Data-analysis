import type { ToolKey } from "../types/pipeline";

type ToolbarButton = {
  key: ToolKey;
  title: string;
  icon: React.ComponentType<{ size?: number }>;
};

type ToolbarProps = {
  toolbarButtons: ToolbarButton[];
  activeTool: ToolKey;
  onToolClick: (tool: ToolKey) => void;
};

export function Toolbar({
  toolbarButtons,
  activeTool,
  onToolClick,
}: ToolbarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 bg-white px-4 py-3">
      {toolbarButtons.map((tool) => {
        const Icon = tool.icon;

        return (
          <button
            key={tool.key}
            type="button"
            title={tool.title}
            onClick={() => onToolClick(tool.key)}
            className={`flex h-10 w-10 items-center justify-center rounded-xl border text-sm shadow-sm transition hover:-translate-y-0.5 hover:bg-blue-50 ${
              activeTool === tool.key
                ? "border-blue-500 bg-blue-100 text-blue-700"
                : "border-slate-200 bg-white text-slate-700"
            }`}
          >
            <Icon size={18} />
          </button>
        );
      })}
    </div>
  );
}