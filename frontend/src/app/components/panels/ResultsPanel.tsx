type ResultsPanelProps = {
  logs: string[];
};

export function ResultsPanel({ logs }: ResultsPanelProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold">Results / Log</h3>

      <div className="rounded-xl border border-slate-200 bg-slate-950 p-3 text-xs text-slate-100">
        <div className="max-h-96 overflow-auto whitespace-pre-wrap font-mono">
          {logs.length > 0 ? logs.join("\n") : "No logs yet."}
        </div>
      </div>
    </div>
  );
}