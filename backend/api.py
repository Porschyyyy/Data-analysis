from pathlib import Path
from typing import Literal
from fastapi.responses import FileResponse

from fastapi import UploadFile, File
import shutil
import uuid

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from io import BytesIO
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits
from fastapi import Response

from fits_utils import (
    read_all_headers,
    summarize_header_values,
    add_standard_columns,
    make_all_groups)

from calibration import (
    create_master_bias,
    create_master_dark,
    create_master_flat,
    calibrate_light_files)

from trim_utils import run_center_trim, summarize_image_shapes
from cosmic_ray import run_cosmic_ray_removal
from alignment import run_centroid_alignment
from photometry import run_aperture_photometry
from plot_lightcurve import plot_lightcurve
from transit_model import fit_transit

PIPELINE_PROGRESS = {
    "current": 0,
    "total": 0,
    "message": "Ready",
    "running": False}

def set_progress(current=0, total=0, message="Ready", running=False, step="idle"):
    PIPELINE_PROGRESS.update({
        "current": int(current),
        "total": int(total),
        "message": message,
        "running": running,
        "step": step})

app = FastAPI(
    title="WASP-12b Data Analysis API",
    version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"])


# ==================================================
# Helper functions
# ==================================================

def get_fits_files(input_path: str | Path):
    input_path = Path(input_path)

    return sorted(
        list(input_path.rglob("*.fits")) +
        list(input_path.rglob("*.fit")) +
        list(input_path.rglob("*.fts")))


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
        .replace("'", ""))


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


class LightCurveRequest(BaseModel):
    photometry_csv: str
    output_png: str

    remove_first_point: bool = False
    remove_outliers: bool = True
    sigma_clip: float | None = None
    bin_size: int | None = None

    mid_transit_jd: float | None = None
    transit_duration_hours: float | None = None

    plot_style: Literal["academic", "line"] = "academic"
    title: str | None = None
    model_type: Literal["data_only", "transit"] = "data_only"


class ListFitsRequest(BaseModel):
    input_path: str


# ==================================================
# Root
# ==================================================

@app.get("/")
def root():
    return {
        "message": "WASP-12b Data Analysis API is running",
        "version": "2.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload-folder")
async def api_upload_folder(files: list[UploadFile] = File(...)):
    session_id = str(uuid.uuid4())[:8]
    upload_root = Path("uploads") / session_id / "raw"
    upload_root.mkdir(parents=True, exist_ok=True)

    saved_files = []

    for file in files:
        filename = Path(file.filename).name
        output_file = upload_root / filename

        with output_file.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        saved_files.append(str(output_file).replace("\\", "/"))

    fits_files = get_fits_files(upload_root)

    return {
        "status": "done",
        "session_id": session_id,
        "raw_path": str(upload_root).replace("\\", "/"),
        "output_path": str((Path("uploads") / session_id / "output")).replace("\\", "/"),
        "n_uploaded": len(saved_files),
        "n_fits_files": len(fits_files),
        "first_file": str(fits_files[0]).replace("\\", "/") if fits_files else None}

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
            "example_files": group_df["filename"].head(3).tolist()})

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
            "summary_csv": str(summary_csv).replace("\\", "/")}

    preview_files = [
        p for p in fits_files
        if is_light_preview_file(p)]

    if len(preview_files) == 0:
        preview_files = fits_files

    first_file = (
        str(preview_files[0]).replace("\\", "/")
        if len(preview_files) > 0
        else None)

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
        "first_preview_file": first_file}


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
                "example_files": group_df["filename"].head(3).tolist()})

        set_progress(
            0,
            len(fits_files),
            "Waiting for frame role assignment",
            False,
            "calibration")

        return {
            "status": "need_frame_role_map",
            "message": "Please assign each detected group to bias/dark/flat/light/skip",
            "detected_groups": detected_groups}

    df = add_standard_columns(
        df,
        frame_role_map=req.frame_role_map)

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
            progress_callback=lambda current, total, message: set_progress(
                current,
                total,
                message,
                True,
                "master_bias"))

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
            progress_callback=lambda current, total, message: set_progress(
                current,
                total,
                message,
                True,
                "master_dark"))
        

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
            progress_callback=lambda current, total, message: set_progress(
                current,
                total,
                message,
                True,
                "master_flat"))

        master_flats[group_value] = output_file

    # Calibrate light frames
    calibrated_path = output_path / "calibrated"
    calibrated_path.mkdir(parents=True, exist_ok=True)

    calibrated_groups = []

    processed_light = 0
    set_progress(0, n_light, "Starting light calibration...", True, "calibration")

    for light_group_value, light_files in groups["light"].items():
        light_meta = group_value_to_dict(
            light_group_value,
            used_keys["light"])

        matched_dark_file = find_matching_master_dark(
            light_meta,
            master_darks,
            used_keys["dark"])

        matched_flat_file = find_matching_master_flat(
            light_meta,
            master_flats,
            used_keys["flat"])

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
            progress_total=n_light)

        processed_light += len(light_files)

        calibrated_groups.append({
            "light_group": str(light_group_value),
            "n_light_files": len(light_files),
            "matched_dark": str(matched_dark_file) if matched_dark_file else None,
            "matched_flat": str(matched_flat_file) if matched_flat_file else None,
            "output_dir": str(group_output_dir)})

        set_progress(
            n_light,
            n_light,
            "Light calibration completed",
            False,
            "calibration")   


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
        "calibrated_groups": calibrated_groups}


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
                detail="target_width and target_height are required when use_common_min_size=False")

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
        ))

    set_progress(len(fits_files), len(fits_files), "Trim completed", False, "trim")

    return {
        "status": "done",
        "step": "trim",
        "input_path": str(input_path),
        "output_path": str(output_path),
        "use_common_min_size": req.use_common_min_size,
        "target_width": req.target_width,
        "target_height": req.target_height,
        "result": str(result)}


@app.post("/trim-summary")
def api_trim_summary(req: TrimRequest):
    input_path = Path(req.input_path)

    if not input_path.exists():
        raise HTTPException(status_code=404, detail=f"input_path not found: {input_path}")

    fits_files = get_fits_files(input_path)

    if len(fits_files) == 0:
        raise HTTPException(status_code=404, detail="No FITS files found")

    df_shape, min_width, min_height, max_width, max_height = summarize_image_shapes(fits_files)

    raw_size_counts = (
        df_shape.groupby(["NAXIS1", "NAXIS2"])
        .size()
        .reset_index(name="count")
        .to_dict(orient="records"))

    size_counts = [
        {
            "width": int(item["NAXIS1"]),
            "height": int(item["NAXIS2"]),
            "count": int(item["count"]),
        }
        for item in raw_size_counts]

    return {
        "status": "done",
        "n_files": int(len(fits_files)),
        "size_counts": size_counts,
        "crop_target": {
            "width": int(min_width),
            "height": int(min_height),
        },
        "min_width": int(min_width),
        "min_height": int(min_height),
        "max_width": int(max_width),
        "max_height": int(max_height)}

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
        ))

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
        "result": str(result)}


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
        ))

    set_progress(len(fits_files), len(fits_files), "Alignment completed", False, "alignment")

    return {
        "status": "done",
        "step": "alignment",
        "input_path": str(input_path),
        "output_path": str(output_path),
        "x_star": req.x_star,
        "y_star": req.y_star,
        "box_size": req.box_size,
        "result": str(result)}


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

    output_png = Path(req.output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)

    set_progress(0, 1, "Generating light curve...", True, "lightcurve")

    if req.model_type == "transit":
        transit_output_png = output_png.with_name(
            output_png.stem + "_transit_fit.png"
        )

        result = fit_transit(
            photometry_csv=str(photometry_csv),
            output_png=str(transit_output_png),
            title=req.title or "Transit Model Fit",
        )

        set_progress(1, 1, "Transit model fit completed", False, "lightcurve")

        return {
            "status": "done",
            "step": "plot_lightcurve",
            "model_type": "transit",
            "photometry_csv": str(photometry_csv),
            "output_png": str(transit_output_png).replace("\\", "/"),
            "result": result,
        }

    result = plot_lightcurve(
        photometry_csv=photometry_csv,
        output_png=output_png,
        remove_first_point=req.remove_first_point,
        remove_outliers=req.remove_outliers,
        sigma_clip=req.sigma_clip,
        bin_size=req.bin_size,
        mid_transit_jd=req.mid_transit_jd,
        transit_duration_hours=req.transit_duration_hours,
        plot_style=req.plot_style,
        title=req.title,
    )

    set_progress(1, 1, "Light curve completed", False, "lightcurve")

    return {
        "status": "done",
        "step": "plot_lightcurve",
        "model_type": "data_only",
        "photometry_csv": str(photometry_csv),
        "output_png": str(result).replace("\\", "/"),
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
            detail=f"File not found: {file_path}")

    return FileResponse(
        file_path,
        filename=file_path.name)


@app.post("/list-fits")
def api_list_fits(req: ListFitsRequest):
    input_path = Path(req.input_path)

    if not input_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"input_path not found: {input_path}")

    fits_files = get_fits_files(input_path)

    preview_files = [
        p for p in fits_files
        if is_light_preview_file(p)]

    if len(preview_files) == 0:
        preview_files = fits_files

    return {
        "status": "done",
        "input_path": str(input_path).replace("\\", "/"),
        "n_files": len(fits_files),
        "files": [str(p).replace("\\", "/") for p in fits_files],
        "first_file": str(preview_files[0]).replace("\\", "/") if len(preview_files) > 0 else None}


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
            detail=f"FITS file not found: {file_path}")

    if downsample < 1:
        raise HTTPException(
            status_code=400,
            detail="downsample must be >= 1")

    try:
        data = fits.getdata(file_path, memmap=False)
        data = np.asarray(data, dtype=np.float32)

        data = np.squeeze(data)

        if data.ndim != 2:
            raise HTTPException(
                status_code=400,
                detail=f"Only 2D FITS images are supported. Got shape {data.shape}")

        original_height, original_width = data.shape

        preview = data[::downsample, ::downsample]

        preview = np.asarray(preview, dtype=np.float32)
        preview[~np.isfinite(preview)] = np.nan

        vmin = np.nanpercentile(preview, percentile_low)
        vmax = np.nanpercentile(preview, percentile_high)

        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
            vmin = np.nanmin(preview)
            vmax = np.nanmax(preview)

        preview_for_display = np.flipud(preview)

        buffer = BytesIO()

        plt.imsave(
            buffer,
            preview_for_display,
            cmap="gray",
            vmin=vmin,
            vmax=vmax,
            format="png")

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
            })

    except HTTPException:
        raise

    except Exception as e:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to preview FITS: {type(e).__name__}: {e}")
    
@app.get("/progress")
def get_progress():
    return PIPELINE_PROGRESS
