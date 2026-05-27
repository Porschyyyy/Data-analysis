from pathlib import Path
from typing import Literal
from fastapi.responses import FileResponse

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from io import BytesIO
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits
from fastapi import Response

import requests
from urllib.parse import quote

from fits_utils import (
    read_all_headers,
    summarize_header_values,
    add_standard_columns,
    summarize_standard_values,
    make_all_groups,
)

from calibration import (
    create_master_bias,
    create_master_dark,
    create_master_flat,
    calibrate_light_files,
)

from trim_utils import run_center_trim
from cosmic_ray import run_cosmic_ray_removal
from alignment import run_centroid_alignment
from photometry import run_aperture_photometry

from plot_lightcurve import (
    plot_lightcurve,
    plot_lightcurve_both_styles,
    plot_phase_folded_lightcurve,
)

PIPELINE_PROGRESS = {
    "current": 0,
    "total": 0,
    "message": "Ready",
    "running": False,
}

def set_progress(current=0, total=0, message="Ready", running=False, step="idle"):
    PIPELINE_PROGRESS.update({
        "current": int(current),
        "total": int(total),
        "message": message,
        "running": running,
        "step": step,
    })

app = FastAPI(
    title="WASP-12b Data Analysis API",
    version="2.0.0",
)

# เผื่อทำ UI ต่อภายหลัง
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# Helper functions
# ==================================================

def get_fits_files(input_path: str | Path):
    input_path = Path(input_path)

    return sorted(
        list(input_path.rglob("*.fits")) +
        list(input_path.rglob("*.fit")) +
        list(input_path.rglob("*.fts"))
    )

def is_light_preview_file(file_path: Path):
    text = f"{file_path.parent.name} {file_path.name}".lower()

    bad_keywords = ["bias", "dark", "flat", "master"]
    if any(key in text for key in bad_keywords):
        return False

    good_keywords = ["light", "object", "wasp", "science"]
    if any(key in text for key in good_keywords):
        return True

    return True

def safe_group_name(value):
    return (
        str(value)
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
        .replace(",", "_")
        .replace("'", "")
    )


def group_value_to_dict(group_value, group_keys):
    if group_value == "all" or len(group_keys) == 0:
        return {}

    if len(group_keys) == 1:
        return {group_keys[0]: group_value}

    return dict(zip(group_keys, group_value))


def find_matching_master_dark(light_meta, master_darks, dark_keys):
    light_exposure = light_meta.get("EXPOSURE_STD")

    for dark_group_value, dark_file in master_darks.items():
        dark_meta = group_value_to_dict(dark_group_value, dark_keys)

        if dark_meta.get("EXPOSURE_STD") == light_exposure:
            return dark_file

    return None


def find_matching_master_flat(light_meta, master_flats, flat_keys):
    light_filter = light_meta.get("FILTER_STD")

    for flat_group_value, flat_file in master_flats.items():
        flat_meta = group_value_to_dict(flat_group_value, flat_keys)

        if flat_meta.get("FILTER_STD") == light_filter:
            return flat_file

    return None


def compute_nearest_mid_transit(start_jd, end_jd, t0, period):
    data_mid = (start_jd + end_jd) / 2.0
    epoch = round((data_mid - t0) / period)
    mid_transit_jd = t0 + epoch * period

    return mid_transit_jd, epoch


def suggest_wasp12b_transit_from_csv(photometry_csv: str | Path):
    photometry_csv = Path(photometry_csv)

    if not photometry_csv.exists():
        raise HTTPException(
            status_code=404,
            detail=f"photometry_csv not found: {photometry_csv}",
        )

    df = pd.read_csv(photometry_csv)

    if "time" not in df.columns:
        raise HTTPException(
            status_code=400,
            detail="photometry_csv must contain column: time",
        )

    df["time"] = pd.to_numeric(df["time"], errors="coerce")
    df = df.dropna(subset=["time"])

    if len(df) == 0:
        raise HTTPException(
            status_code=400,
            detail="No valid time values in photometry_csv",
        )

    start_jd = float(df["time"].min())
    end_jd = float(df["time"].max())
    duration_data_hours = (end_jd - start_jd) * 24.0

    # WASP-12b preset
    t0 = 2454508.97682
    period = 1.09142245
    transit_duration_hours = 2.93

    mid_transit_jd, epoch = compute_nearest_mid_transit(
        start_jd=start_jd,
        end_jd=end_jd,
        t0=t0,
        period=period,
    )

    return {
        "object": "WASP-12b",
        "t0": t0,
        "period_days": period,
        "epoch": epoch,
        "mid_transit_jd": mid_transit_jd,
        "transit_duration_hours": transit_duration_hours,
        "start_jd": start_jd,
        "end_jd": end_jd,
        "data_duration_hours": duration_data_hours,
        "start_minus_mid_hours": (start_jd - mid_transit_jd) * 24.0,
        "end_minus_mid_hours": (end_jd - mid_transit_jd) * 24.0,
    }


def query_nasa_exoplanet_ephemeris(object_name: str):
    object_name = object_name.strip()

    if object_name == "":
        raise HTTPException(
            status_code=400,
            detail="object_name is required",
        )

    query = f"""
    SELECT pl_name, pl_orbper, pl_trandur, pl_tranmid
    FROM pscomppars
    WHERE lower(pl_name) = lower('{object_name}')
    """

    url = (
        "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
        "?query=" + quote(query)
        + "&format=json"
    )

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        rows = response.json()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query NASA Exoplanet Archive: {e}",
        )

    if len(rows) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No exoplanet found in NASA Exoplanet Archive: {object_name}",
        )

    row = rows[0]

    period_days = row.get("pl_orbper")
    duration_hours = row.get("pl_trandur")
    reference_mid_jd = row.get("pl_tranmid")

    missing = []
    if period_days is None:
        missing.append("pl_orbper")
    if duration_hours is None:
        missing.append("pl_trandur")
    if reference_mid_jd is None:
        missing.append("pl_tranmid")

    if len(missing) > 0:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "NASA Exoplanet Archive found the object, but required ephemeris values are missing.",
                "missing_columns": missing,
                "object_name": row.get("pl_name"),
            },
        )

    return {
        "object_name": row.get("pl_name"),
        "period_days": float(period_days),
        "transit_duration_hours": float(duration_hours),
        "reference_mid_transit_jd": float(reference_mid_jd),
        "source": "NASA Exoplanet Archive PSCompPars",
    }


def suggest_exoplanet_transit_from_archive(
    photometry_csv: str | Path,
    object_name: str,
):
    photometry_csv = Path(photometry_csv)

    if not photometry_csv.exists():
        raise HTTPException(
            status_code=404,
            detail=f"photometry_csv not found: {photometry_csv}",
        )

    df = pd.read_csv(photometry_csv)

    if "time" not in df.columns:
        raise HTTPException(
            status_code=400,
            detail="photometry_csv must contain column: time",
        )

    time_values = pd.to_numeric(df["time"], errors="coerce").dropna()

    if len(time_values) == 0:
        raise HTTPException(
            status_code=400,
            detail="No valid time values in photometry_csv",
        )

    start_jd = float(time_values.min())
    end_jd = float(time_values.max())
    center_jd = (start_jd + end_jd) / 2.0
    duration_data_hours = (end_jd - start_jd) * 24.0

    ephem = query_nasa_exoplanet_ephemeris(object_name)

    t0 = ephem["reference_mid_transit_jd"]
    period = ephem["period_days"]

    epoch = round((center_jd - t0) / period)
    mid_transit_jd = t0 + epoch * period

    return {
        **ephem,
        "epoch": int(epoch),
        "mid_transit_jd": float(mid_transit_jd),
        "start_jd": start_jd,
        "end_jd": end_jd,
        "center_jd": center_jd,
        "data_duration_hours": duration_data_hours,
        "start_minus_mid_hours": (start_jd - mid_transit_jd) * 24.0,
        "end_minus_mid_hours": (end_jd - mid_transit_jd) * 24.0,
    }

# ==================================================
# Request Models
# ==================================================

class HeaderRequest(BaseModel):
    raw_path: str
    output_path: str | None = None


class CalibrationRequest(BaseModel):
    raw_path: str
    output_path: str
    combine_method: Literal["mean", "median"] = "median"
    frame_role_map: dict[str, str] | None = None


class TrimRequest(BaseModel):
    input_path: str
    output_path: str
    target_width: int | None = None
    target_height: int | None = None
    use_common_min_size: bool = True


class CosmicRayRequest(BaseModel):
    input_path: str
    output_path: str
    tile_size: int = 512
    sigclip: float = 4.5
    sigfrac: float = 0.3
    objlim: float = 5.0


class AlignmentRequest(BaseModel):
    input_path: str
    output_path: str
    x_star: float
    y_star: float
    box_size: int = 50


class PhotometryRequest(BaseModel):
    input_path: str
    output_csv: str

    # positions[0] = target, positions[1:] = comparison stars
    positions: list[list[float]]

    aperture_radius: float | None = None
    annulus_inner: float | None = None
    annulus_outer: float | None = None
    centroid_box_size: int | None = None
    recenter: bool = True
    auto_params: bool = True


class TransitSuggestionRequest(BaseModel):
    photometry_csv: str


class ExoplanetEphemerisRequest(BaseModel):
    photometry_csv: str
    object_name: str


class LightCurveRequest(BaseModel):
    photometry_csv: str
    output_png: str | None = None
    output_dir: str | None = None

    show: bool = False
    remove_first_point: bool = False
    remove_outliers: bool = True

    sigma_clip: float | None = None
    bin_size: int | None = None

    mid_transit_jd: float | None = None
    transit_duration_hours: float | None = None

    use_exoplanet_archive: bool = False
    object_name: str | None = None

    make_both_styles: bool = True
    make_phase_plot: bool = False
    t0: float | None = None
    period: float | None = None

    plot_style: Literal["1", "2"] = "1"
    title: str | None = None

class FolderDialogRequest(BaseModel):
    title: str = "Choose folder"
    initial_dir: str | None = None

class ListFitsRequest(BaseModel):
    input_path: str

# ==================================================
# Root
# ==================================================

@app.get("/")
def root():
    return {
        "message": "WASP-12b Data Analysis API is running",
        "version": "2.0.0",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/choose-folder")
def api_choose_folder(req: FolderDialogRequest):
    try:
        from tkinter import Tk, filedialog

        root = Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        options = {
            "title": req.title,
        }

        if req.initial_dir is not None:
            initial_dir = Path(req.initial_dir)

            if initial_dir.exists():
                options["initialdir"] = str(initial_dir)

        folder = filedialog.askdirectory(**options)

        root.destroy()

        if folder == "":
            return {
                "status": "cancelled",
                "path": None,
            }

        folder = folder.replace("\\", "/")

        return {
            "status": "done",
            "path": folder,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to open folder dialog: {e}",
        )


# ==================================================
# FITS Headers
# ==================================================

@app.post("/read-headers")
def api_read_headers(req: HeaderRequest):
    raw_path = Path(req.raw_path)

    if not raw_path.exists():
        raise HTTPException(status_code=404, detail=f"raw_path not found: {raw_path}")

    fits_files = get_fits_files(raw_path)

    if len(fits_files) == 0:
        set_progress(0, 0, "No FITS files found", False, "headers")
        raise HTTPException(status_code=404, detail="No FITS files found")

    set_progress(0, len(fits_files), "Reading FITS headers...", True, "headers")

    headers_df = read_all_headers(fits_files)
    summary = summarize_header_values(headers_df)

    df_std = add_standard_columns(headers_df)

    detected_groups = []

    for group_name, group_df in df_std.groupby("RAW_FRAME_GROUP", dropna=False):
        detected_groups.append({
            "group_name": str(group_name),
            "n_files": len(group_df),
            "example_files": group_df["filename"].head(3).tolist(),
        })

    saved_files = {}

    if req.output_path is not None:
        output_path = Path(req.output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        headers_csv = output_path / "fits_headers_raw.csv"
        summary_csv = output_path / "header_summary.csv"

        headers_df.to_csv(headers_csv, index=False)
        summary.to_csv(summary_csv, index=False)

        saved_files = {
            "headers_csv": str(headers_csv).replace("\\", "/"),
            "summary_csv": str(summary_csv).replace("\\", "/"),
        }

    preview_files = [
        p for p in fits_files
        if is_light_preview_file(p)
    ]

    if len(preview_files) == 0:
        preview_files = fits_files

    first_file = (
        str(preview_files[0]).replace("\\", "/")
        if len(preview_files) > 0
        else None
    )

    set_progress(len(fits_files), len(fits_files), "Headers completed", False, "headers")

    return {
        "status": "done",
        "step": "read_headers",
        "raw_path": str(raw_path).replace("\\", "/"),
        "output_path": str(req.output_path).replace("\\", "/") if req.output_path else None,
        "n_files": len(headers_df),
        "columns": list(headers_df.columns),
        "summary": summary.to_dict(orient="records"),
        "detected_groups": detected_groups,
        "saved_files": saved_files,
        "first_preview_file": first_file,
    }


# ==================================================
# Calibration
# ==================================================

@app.post("/run-calibration")
def api_run_calibration(req: CalibrationRequest):
    raw_path = Path(req.raw_path)
    output_path = Path(req.output_path)

    if not raw_path.exists():
        raise HTTPException(status_code=404, detail=f"raw_path not found: {raw_path}")

    output_path.mkdir(parents=True, exist_ok=True)

    fits_files = get_fits_files(raw_path)

    if len(fits_files) == 0:
        set_progress(0, 0, "No FITS files found", False, "calibration")
        raise HTTPException(status_code=404, detail="No FITS files found")

    set_progress(0, len(fits_files), "Starting calibration...", True, "calibration")

    metadata_file = output_path / "fits_headers_raw.csv"

    if metadata_file.exists():
        df = pd.read_csv(metadata_file)
    else:
        df = read_all_headers(fits_files)

    df = add_standard_columns(df)

    if req.frame_role_map is None:
        detected_groups = []

        for group_name, group_df in df.groupby("RAW_FRAME_GROUP", dropna=False):
            detected_groups.append({
                "group_name": str(group_name),
                "n_files": len(group_df),
                "example_files": group_df["filename"].head(3).tolist(),
            })

        set_progress(
            0,
            len(fits_files),
            "Waiting for frame role assignment",
            False,
            "calibration",
)

        return {
            "status": "need_frame_role_map",
            "message": "Please assign each detected group to bias/dark/flat/light/skip",
            "detected_groups": detected_groups,
        }

    df = add_standard_columns(
        df,
        frame_role_map=req.frame_role_map,
    )

    df.to_csv(output_path / "fits_metadata_standard.csv", index=False)

    groups, used_keys = make_all_groups(df)

    n_bias = sum(len(files) for files in groups["bias"].values())
    n_dark = sum(len(files) for files in groups["dark"].values())
    n_flat = sum(len(files) for files in groups["flat"].values())
    n_light = sum(len(files) for files in groups["light"].values())

    master_path = output_path / "master"
    master_path.mkdir(parents=True, exist_ok=True)

    overscan_slice = None
    trim_slice = None

    set_progress(0, len(fits_files), "Creating master bias...", True, "calibration")

    # Master bias
    master_bias = None
    master_bias_file = None

    bias_groups = groups["bias"]

    if len(bias_groups) > 0:
        first_bias_group = list(bias_groups.values())[0]
        master_bias_file = master_path / "master_bias.fits"

        master_bias = create_master_bias(
            bias_files=first_bias_group,
            output_file=master_bias_file,
            overscan_slice=overscan_slice,
            trim_slice=trim_slice,
            combine_method=req.combine_method,
            skip_existing=False,
        )

    set_progress(0, len(fits_files), "Creating master dark...", True, "calibration")
    set_progress(n_bias, n_bias, "Master bias completed", True, "master_bias")

    # Master dark
    master_darks = {}

    for group_value, dark_files in groups["dark"].items():
        output_file = master_path / f"master_dark_{safe_group_name(group_value)}.fits"

        create_master_dark(
            dark_files=dark_files,
            output_file=output_file,
            master_bias=master_bias,
            overscan_slice=overscan_slice,
            trim_slice=trim_slice,
            combine_method=req.combine_method,
            skip_existing=False,
        )

        master_darks[group_value] = output_file

    set_progress(0, len(fits_files), "Creating master flat...", True, "calibration")

    # Master flat
    master_flats = {}

    for group_value, flat_files in groups["flat"].items():
        output_file = master_path / f"master_flat_{safe_group_name(group_value)}.fits"

        create_master_flat(
            flat_files=flat_files,
            output_file=output_file,
            master_bias=master_bias,
            master_dark=None,
            overscan_slice=overscan_slice,
            trim_slice=trim_slice,
            combine_method=req.combine_method,
            skip_existing=False,
        )

        master_flats[group_value] = output_file

    # Calibrate light frames
    calibrated_path = output_path / "calibrated"
    calibrated_path.mkdir(parents=True, exist_ok=True)

    calibrated_groups = []

    processed_light = 0

    for light_group_value, light_files in groups["light"].items():
        light_meta = group_value_to_dict(
            light_group_value,
            used_keys["light"],
        )

        matched_dark_file = find_matching_master_dark(
            light_meta,
            master_darks,
            used_keys["dark"],
        )

        matched_flat_file = find_matching_master_flat(
            light_meta,
            master_flats,
            used_keys["flat"],
        )

        group_output_dir = calibrated_path / safe_group_name(light_group_value)

        calibrate_light_files(
            light_files=light_files,
            output_dir=group_output_dir,
            master_bias_file=master_bias_file,
            master_dark_file=matched_dark_file,
            master_flat_file=matched_flat_file,
            overscan_slice=overscan_slice,
            trim_slice=trim_slice,
            skip_existing=False,
            progress_callback=lambda current, total, message: set_progress(
                current,
                total,
                message,
                True,
                "calibration",
            ),
            progress_start=processed_light,
            progress_total=sum(len(files) for files in groups["light"].values()),
        )

        processed_light += len(light_files)

        calibrated_groups.append({
            "light_group": str(light_group_value),
            "n_light_files": len(light_files),
            "matched_dark": str(matched_dark_file) if matched_dark_file else None,
            "matched_flat": str(matched_flat_file) if matched_flat_file else None,
            "output_dir": str(group_output_dir),
        })

        set_progress(
            len(fits_files),
            len(fits_files),
            "Calibration completed",
            False,
            "calibration",
        )


    return {
        "status": "done",
        "step": "calibration",
        "raw_path": str(raw_path),
        "output_path": str(output_path),
        "master_path": str(master_path),
        "calibrated_path": str(calibrated_path),
        "n_fits_files": len(fits_files),
        "n_bias_groups": len(groups["bias"]),
        "n_dark_groups": len(groups["dark"]),
        "n_flat_groups": len(groups["flat"]),
        "n_light_groups": len(groups["light"]),
        "calibrated_groups": calibrated_groups,
    }


# ==================================================
# Trim
# ==================================================

@app.post("/run-trim")
def api_run_trim(req: TrimRequest):
    input_path = Path(req.input_path)
    output_path = Path(req.output_path)

    if not input_path.exists():
        set_progress(0, 0, "Input path not found", False, "trim")
        raise HTTPException(status_code=404, detail=f"input_path not found: {input_path}")

    fits_files = get_fits_files(input_path)
    set_progress(0, len(fits_files), "Running trim...", True, "trim")

    if not req.use_common_min_size:
        if req.target_width is None or req.target_height is None:
            raise HTTPException(
                status_code=400,
                detail="target_width and target_height are required when use_common_min_size=False",
            )

    output_path.mkdir(parents=True, exist_ok=True)

    result = run_center_trim(
        input_path=input_path,
        output_path=output_path,
        target_width=req.target_width,
        target_height=req.target_height,
        use_common_min_size=req.use_common_min_size,
        skip_existing=False,
        progress_callback=lambda current, total, message: set_progress(
            current, total, message, True, "trim"
        ),
    )

    set_progress(len(fits_files), len(fits_files), "Trim completed", False, "trim")

    return {
        "status": "done",
        "step": "trim",
        "input_path": str(input_path),
        "output_path": str(output_path),
        "use_common_min_size": req.use_common_min_size,
        "target_width": req.target_width,
        "target_height": req.target_height,
        "result": str(result),
    }


# ==================================================
# Cosmic Ray Removal
# ==================================================

@app.post("/run-cosmic-ray")
def api_run_cosmic_ray(req: CosmicRayRequest):
    input_path = Path(req.input_path)
    output_path = Path(req.output_path)

    if not input_path.exists():
        set_progress(0, 0, "Input path not found", False, "cosmic_ray")
        raise HTTPException(status_code=404, detail=f"input_path not found: {input_path}")

    fits_files = get_fits_files(input_path)
    set_progress(0, len(fits_files), "Removing cosmic rays...", True, "cosmic_ray")

    output_path.mkdir(parents=True, exist_ok=True)

    result = run_cosmic_ray_removal(
        input_path=input_path,
        output_path=output_path,
        tile_size=req.tile_size,
        sigclip=req.sigclip,
        sigfrac=req.sigfrac,
        objlim=req.objlim,
        skip_existing=False,
        progress_callback=lambda current, total, message: set_progress(
            current, total, message, True, "cosmic_ray"
        ),
    )

    set_progress(len(fits_files), len(fits_files), "Cosmic ray removal completed", False, "cosmic_ray")

    return {
        "status": "done",
        "step": "cosmic_ray",
        "input_path": str(input_path),
        "output_path": str(output_path),
        "tile_size": req.tile_size,
        "sigclip": req.sigclip,
        "sigfrac": req.sigfrac,
        "objlim": req.objlim,
        "result": str(result),
    }


# ==================================================
# Alignment
# ==================================================

@app.post("/run-alignment")
def api_run_alignment(req: AlignmentRequest):
    input_path = Path(req.input_path)
    output_path = Path(req.output_path)

    if not input_path.exists():
        set_progress(0, 0, "Input path not found", False, "alignment")
        raise HTTPException(status_code=404, detail=f"input_path not found: {input_path}")

    fits_files = get_fits_files(input_path)
    set_progress(0, len(fits_files), "Running alignment...", True, "alignment")

    output_path.mkdir(parents=True, exist_ok=True)

    result = run_centroid_alignment(
        input_path=input_path,
        output_path=output_path,
        x_star=req.x_star,
        y_star=req.y_star,
        box_size=req.box_size,
        skip_existing=False,
        progress_callback=lambda current, total, message: set_progress(
            current, total, message, True, "alignment"
        ),
    )

    set_progress(len(fits_files), len(fits_files), "Alignment completed", False, "alignment")

    return {
        "status": "done",
        "step": "alignment",
        "input_path": str(input_path),
        "output_path": str(output_path),
        "x_star": req.x_star,
        "y_star": req.y_star,
        "box_size": req.box_size,
        "result": str(result),
    }


# ==================================================
# Photometry
# ==================================================

@app.post("/run-photometry")
def api_run_photometry(req: PhotometryRequest):
    input_path = Path(req.input_path)
    output_csv = Path(req.output_csv)

    if not input_path.exists():
        set_progress(0, 0, "Input path not found", False, "photometry")
        raise HTTPException(status_code=404, detail=f"input_path not found: {input_path}")

    fits_files = get_fits_files(input_path)
    set_progress(0, len(fits_files), "Running photometry...", True, "photometry")

    if len(req.positions) < 2:
        raise HTTPException(
            status_code=400,
            detail="positions must contain at least 2 stars: target + 1 comparison",
        )

    positions = []

    for i, item in enumerate(req.positions):
        if len(item) != 2:
            raise HTTPException(
                status_code=400,
                detail=f"positions[{i}] must be [x, y]",
            )

        positions.append((float(item[0]), float(item[1])))

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    df = run_aperture_photometry(
        input_path=input_path,
        output_csv=output_csv,
        positions=positions,
        aperture_radius=req.aperture_radius,
        annulus_inner=req.annulus_inner,
        annulus_outer=req.annulus_outer,
        centroid_box_size=req.centroid_box_size,
        recenter=req.recenter,
        auto_params=req.auto_params,
        progress_callback=lambda current, total, message: set_progress(
            current, total, message, True, "photometry"
        ),
    )

    set_progress(len(fits_files), len(fits_files), "Photometry completed", False, "photometry")

    return {
        "status": "done",
        "step": "photometry",
        "input_path": str(input_path),
        "output_csv": str(output_csv),
        "n_rows": int(len(df)),
        "columns": list(df.columns) if len(df) > 0 else [],
    }


# ==================================================
# Transit Suggestion
# ==================================================

@app.post("/suggest-transit")
def api_suggest_transit(req: TransitSuggestionRequest):
    result = suggest_wasp12b_transit_from_csv(req.photometry_csv)

    return {
        "status": "done",
        "step": "suggest_transit",
        **result,
    }


@app.post("/suggest-exoplanet-transit")
def api_suggest_exoplanet_transit(req: ExoplanetEphemerisRequest):
    result = suggest_exoplanet_transit_from_archive(
        photometry_csv=req.photometry_csv,
        object_name=req.object_name,
    )

    return {
        "status": "done",
        "step": "suggest_exoplanet_transit",
        **result,
    }

# ==================================================
# Plot Light Curve
# ==================================================

@app.post("/plot-lightcurve")
def api_plot_lightcurve(req: LightCurveRequest):
    photometry_csv = Path(req.photometry_csv)

    if not photometry_csv.exists():
        set_progress(0, 0, "Photometry CSV not found", False, "lightcurve")
        raise HTTPException(
            status_code=404,
            detail=f"photometry_csv not found: {photometry_csv}",
        )

    set_progress(0, 1, "Plotting light curve...", True, "lightcurve")
    
    if not req.make_both_styles:
        raise HTTPException(
            status_code=400,
            detail="This API currently supports make_both_styles=True only.",
        )

    mid_transit_jd = req.mid_transit_jd
    transit_duration_hours = req.transit_duration_hours
    transit_suggestion = None
    phase_png = None

    if req.use_exoplanet_archive:
        if req.object_name is None or req.object_name.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="object_name is required when use_exoplanet_archive=True",
            )

        transit_suggestion = suggest_exoplanet_transit_from_archive(
            photometry_csv=photometry_csv,
            object_name=req.object_name,
        )

        mid_transit_jd = transit_suggestion["mid_transit_jd"]
        transit_duration_hours = transit_suggestion["transit_duration_hours"]

    if req.make_both_styles:
        if req.output_dir is not None:
            output_dir = Path(req.output_dir)
        elif req.output_png is not None:
            output_dir = Path(req.output_png).parent
        else:
            output_dir = photometry_csv.parent

        output_dir.mkdir(parents=True, exist_ok=True)

        result = plot_lightcurve_both_styles(
            photometry_csv=photometry_csv,
            output_dir=output_dir,
            show=False,
            remove_first_point=req.remove_first_point,
            remove_outliers=req.remove_outliers,
            sigma_clip=req.sigma_clip,
            bin_size=req.bin_size,
            mid_transit_jd=mid_transit_jd,
            transit_duration_hours=transit_duration_hours,
            title=req.title,
        )

        set_progress(1, 1, "Light curve completed", False, "lightcurve")

        return {
            "status": "done",
            "step": "plot_lightcurve",
            "mode": "both_styles",
            "photometry_csv": str(photometry_csv),
            "output_dir": str(output_dir),
            "academic_png": result["academic_png"],
            "line_png": result["line_png"],
            "phase_png": str(phase_png) if phase_png else None,
            "mid_transit_jd": mid_transit_jd,
            "transit_duration_hours": transit_duration_hours,
            "transit_suggestion": transit_suggestion,
        }

    if req.output_png is None:
        raise HTTPException(
            status_code=400,
            detail="output_png is required when make_both_styles=False",
        )

    output_png = Path(req.output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)

    result = plot_lightcurve_both_styles(
        photometry_csv=photometry_csv,
        output_dir=output_dir,
        show=False,
        remove_first_point=req.remove_first_point,
        remove_outliers=req.remove_outliers,
        sigma_clip=req.sigma_clip,
        bin_size=req.bin_size,
        mid_transit_jd=mid_transit_jd,
        transit_duration_hours=transit_duration_hours,
        title=req.title,
    )

    phase_png = None

    if req.make_phase_plot:
        phase_t0 = req.t0
        phase_period = req.period

        if req.use_exoplanet_archive:
            if transit_suggestion is None:
                if req.object_name is None or req.object_name.strip() == "":
                    raise HTTPException(
                        status_code=400,
                        detail="object_name is required when use_exoplanet_archive=True",
                    )

                transit_suggestion = suggest_exoplanet_transit_from_archive(
                    photometry_csv=photometry_csv,
                    object_name=req.object_name,
                )

            phase_t0 = transit_suggestion["reference_mid_transit_jd"]
            phase_period = transit_suggestion["period_days"]

        if phase_t0 is None or phase_period is None:
            raise HTTPException(
                status_code=400,
                detail="t0 and period are required for phase plot, or use_exoplanet_archive=True with object_name.",
            )

        phase_png = output_dir / "lightcurve_phase_folded.png"

        plot_phase_folded_lightcurve(
            photometry_csv=photometry_csv,
            output_png=phase_png,
            t0=phase_t0,
            period=phase_period,
            show=False,
            title=req.title or "Phase-folded Light Curve",
        )

    return {
        "status": "done",
        "step": "plot_lightcurve",
        "mode": "both_styles",
        "photometry_csv": str(photometry_csv),
        "output_dir": str(output_dir),
        "academic_png": result["academic_png"],
        "line_png": result["line_png"],
        "phase_png": str(phase_png) if phase_png else None,
        "mid_transit_jd": mid_transit_jd,
        "transit_duration_hours": transit_duration_hours,
        "transit_suggestion": transit_suggestion,
    }

# ==================================================
# Serve Output File
# ==================================================

@app.get("/file")
def api_get_file(path: str):
    file_path = Path(path)

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_path}",
        )

    return FileResponse(
        file_path,
        media_type="image/png",
        filename=file_path.name,
    )


@app.post("/list-fits")
def api_list_fits(req: ListFitsRequest):
    input_path = Path(req.input_path)

    if not input_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"input_path not found: {input_path}",
        )

    fits_files = get_fits_files(input_path)

    preview_files = [
        p for p in fits_files
        if is_light_preview_file(p)
    ]

    if len(preview_files) == 0:
        preview_files = fits_files

    return {
        "status": "done",
        "input_path": str(input_path).replace("\\", "/"),
        "n_files": len(fits_files),
        "files": [str(p).replace("\\", "/") for p in fits_files],
        "first_file": str(preview_files[0]).replace("\\", "/") if len(preview_files) > 0 else None,
    }


# ==================================================
# FITS Preview
# ==================================================

@app.get("/preview-fits")
def api_preview_fits(
    path: str,
    downsample: int = 8,
    percentile_low: float = 1.0,
    percentile_high: float = 99.5,
):
    file_path = Path(path)

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"FITS file not found: {file_path}",
        )

    if downsample < 1:
        raise HTTPException(
            status_code=400,
            detail="downsample must be >= 1",
        )

    try:
        data = fits.getdata(file_path, memmap=False)
        data = np.asarray(data, dtype=np.float32)

        # ถ้า FITS เป็น 3D ให้ squeeze เหลือ 2D ถ้าทำได้
        data = np.squeeze(data)

        if data.ndim != 2:
            raise HTTPException(
                status_code=400,
                detail=f"Only 2D FITS images are supported. Got shape {data.shape}",
            )

        original_height, original_width = data.shape

        # ทำภาพย่อ
        preview = data[::downsample, ::downsample]

        preview = np.asarray(preview, dtype=np.float32)
        preview[~np.isfinite(preview)] = np.nan

        vmin = np.nanpercentile(preview, percentile_low)
        vmax = np.nanpercentile(preview, percentile_high)

        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
            vmin = np.nanmin(preview)
            vmax = np.nanmax(preview)

        # ให้ภาพแสดงแบบ origin="lower" เหมือน matplotlib / AstroImageJ style
        preview_for_display = np.flipud(preview)

        buffer = BytesIO()

        plt.imsave(
            buffer,
            preview_for_display,
            cmap="gray",
            vmin=vmin,
            vmax=vmax,
            format="png",
        )

        buffer.seek(0)

        return Response(
            content=buffer.getvalue(),
            media_type="image/png",
            headers={
                "X-FITS-Width": str(original_width),
                "X-FITS-Height": str(original_height),
                "X-Preview-Width": str(preview.shape[1]),
                "X-Preview-Height": str(preview.shape[0]),
                "X-Downsample": str(downsample),
            },
        )

    except HTTPException:
        raise

    except Exception as e:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to preview FITS: {type(e).__name__}: {e}",
        )
    
@app.get("/progress")
def get_progress():
    return PIPELINE_PROGRESS