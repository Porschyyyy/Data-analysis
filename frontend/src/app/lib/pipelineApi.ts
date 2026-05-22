import { API_BASE } from "./constants";
import type { AddLog } from "../types/pipeline";

export async function callApi(endpoint: string, body: unknown, addLog: AddLog) {
  addLog(`POST ${endpoint}`);

  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "API error");
  }

  addLog(`DONE ${endpoint}`);
  return data;
}

export async function chooseFolderRequest(
  target: "raw" | "output",
  currentPath: string,
  addLog: AddLog
) {
  const title = target === "raw" ? "เลือกโฟลเดอร์ raw FITS" : "เลือกโฟลเดอร์ output";
  addLog(`OPEN FOLDER DIALOG: ${title}`);

  const res = await fetch(`${API_BASE}/choose-folder`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, initial_dir: currentPath || null }),
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Folder dialog error");
  }

  return data as { path?: string | null };
}

export async function listFitsRequest(inputPath: string, addLog: AddLog) {
  const data = await callApi("/list-fits", { input_path: inputPath }, addLog)

  return data as {
    status: string
    input_path: string
    n_files: number
    files: string[]
    first_file: string | null
  }
}

export async function readHeadersRequest(
  rawPath: string,
  outputPath: string,
  addLog: AddLog
) {
  const data = await callApi(
    "/read-headers",
    {
      raw_path: rawPath,
      output_path: outputPath,
    },
    addLog
  )

  return data as {
    status: string
    step: string
    raw_path: string
    output_path: string | null
    n_files: number
    columns: string[]
    summary: Record<string, unknown>[]
    saved_files: {
      headers_csv?: string
      summary_csv?: string
    }
    first_preview_file: string | null
  }
}