import type { TabKey } from "../types/pipeline";

type TabItem = {
  key: TabKey;
  label: string;
};

type TabBarProps = {
  tabs: TabItem[];
  activeTab: TabKey;
  onTabClick: (tab: TabKey) => void;
};

export function TabBar({ tabs, activeTab, onTabClick }: TabBarProps) {
  return (
    <nav className="flex flex-wrap gap-1 border-b border-slate-300 bg-slate-100 px-2 pt-2">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          onClick={() => onTabClick(tab.key)}
          className={`rounded-t-xl border border-b-0 px-4 py-2 text-sm transition ${
            activeTab === tab.key
              ? "border-slate-300 bg-white font-semibold text-slate-950"
              : "border-slate-300 bg-slate-50 text-slate-600 hover:bg-white"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}