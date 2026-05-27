import React from "react";

type DetectedGroup = {
  group_name: string;
  n_files: number;
  example_files: string[];
};

type CalibrationPanelProps = {
  detectedGroups: DetectedGroup[];
  frameRoleMap: Record<string, string>;
  setFrameRoleMap: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  runCalibrationOnly: () => void;
};

export function CalibrationPanel({
  detectedGroups,
  frameRoleMap,
  setFrameRoleMap,
  runCalibrationOnly,
}: CalibrationPanelProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold">Calibration</h3>

      <p className="text-sm text-slate-500">
        Assign each detected group, then run calibration to create master files
        and calibrated light frames.
      </p>

      {detectedGroups.length > 0 && (
        <div className="space-y-3">
          <h4 className="font-semibold">Assign frame groups</h4>

          {detectedGroups.map((group) => (
            <div
              key={group.group_name}
              className="rounded-lg border border-slate-200 bg-white p-3"
            >
              <p className="text-sm font-semibold">{group.group_name}</p>
              <p className="text-xs text-slate-500">Files: {group.n_files}</p>
              <p className="text-xs text-slate-500">
                Example: {group.example_files.join(", ")}
              </p>

              <select
                value={frameRoleMap[group.group_name] ?? ""}
                onChange={(e) =>
                  setFrameRoleMap((prev) => ({
                    ...prev,
                    [group.group_name]: e.target.value,
                  }))
                }
                className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                <option value="" disabled>
                  Select group...
                </option>

                {group.group_name.toLowerCase().includes("bias") && (
                  <option value="bias">bias</option>
                )}

                {group.group_name.toLowerCase().includes("dark") && (
                  <option value="dark">dark</option>
                )}

                {group.group_name.toLowerCase().includes("flat") && (
                  <option value="flat">flat</option>
                 )}

                {(group.group_name.toLowerCase().includes("light") ||
                  group.group_name.toLowerCase().includes("object")) && (
                  <option value="light">light</option>
                  )}
                </select>
            </div>
          ))}
        </div>
      )}

      <button
        type="button"
        onClick={runCalibrationOnly}
        className="w-full rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
      >
        Run Calibration
      </button>
    </div>
  );
}