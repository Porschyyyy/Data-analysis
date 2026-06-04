from pathlib import Path
from astropy.io import fits
import numpy as np
import pandas as pd


def get_fits_files(input_path):
    input_path = Path(input_path)

    return sorted(
        list(input_path.rglob("*.fits")) +
        list(input_path.rglob("*.fit")) +
        list(input_path.rglob("*.fts")))


def summarize_image_shapes(files):
    rows = []

    for f in files:
        hdr = fits.getheader(f)

        rows.append({
            "file": str(f),
            "filename": Path(f).name,
            "folder": Path(f).parent.name,
            "NAXIS1": hdr.get("NAXIS1"),
            "NAXIS2": hdr.get("NAXIS2")})

    df_shape = pd.DataFrame(rows)

    min_width = int(df_shape["NAXIS1"].min())
    min_height = int(df_shape["NAXIS2"].min())

    max_width = int(df_shape["NAXIS1"].max())
    max_height = int(df_shape["NAXIS2"].max())

    return df_shape, min_width, min_height, max_width, max_height


def compute_center_trim_box(image_shape, target_width, target_height):
    ny, nx = image_shape

    if target_width > nx:
        raise ValueError(f"target_width {target_width} ใหญ่กว่า image width {nx}")

    if target_height > ny:
        raise ValueError(f"target_height {target_height} ใหญ่กว่า image height {ny}")

    x0 = (nx - target_width) // 2
    y0 = (ny - target_height) // 2

    x1 = x0 + target_width
    y1 = y0 + target_height

    return int(x0), int(x1), int(y0), int(y1)


def trim_one_fits_file(
    input_file,
    output_file,
    x0,
    x1,
    y0,
    y1,
    skip_existing=False
):

    input_file = Path(input_file)
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if skip_existing and output_file.exists():
        print(f"Skip trimmed existing: {output_file.name}")
        return

    data, header = fits.getdata(input_file, header=True, memmap=True)
    data = np.asarray(data, dtype=np.float32)

    trimmed = data[y0:y1, x0:x1].astype(np.float32)

    header["HISTORY"] = "Fixed center trim applied"
    header["TRIMX0"] = int(x0)
    header["TRIMX1"] = int(x1)
    header["TRIMY0"] = int(y0)
    header["TRIMY1"] = int(y1)
    header["BZERO"] = 0
    header["BSCALE"] = 1

    fits.writeto(
        output_file,
        trimmed,
        header=header,
        overwrite=True)

    del data
    del trimmed


def run_center_trim(
    input_path,
    output_path,
    target_width=None,
    target_height=None,
    use_common_min_size=False,
    skip_existing=False,
    progress_callback=None,
):
    
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    fits_files = get_fits_files(input_path)

    print("\n========== CENTER TRIM ==========")
    print("Input :", input_path)
    print("Output:", output_path)
    print("Number of files:", len(fits_files))

    if len(fits_files) == 0:
        print("No FITS files found for trimming")
        return {
            "n_files": 0,
            "target_width": None,
            "target_height": None,
            "use_common_min_size": use_common_min_size,
            "message": "No FITS files found for trimming"}

    df_shape, min_width, min_height, max_width, max_height = summarize_image_shapes(fits_files)

    first_data = fits.getdata(fits_files[0], memmap=False)
    image_shape = first_data.shape
    del first_data

    if use_common_min_size:
        target_width = min_width
        target_height = min_height

    if target_width is None or target_height is None:
        raise ValueError("ต้องกำหนด target_width/target_height หรือ use_common_min_size=True")

    x0, x1, y0, y1 = compute_center_trim_box(
        image_shape=image_shape,
        target_width=target_width,
        target_height=target_height)

    print("\nTrim box:")
    print("x0, x1 =", x0, x1)
    print("y0, y1 =", y0, y1)
    print("Trimmed size:", y1 - y0, "x", x1 - x0)

    for i, input_file in enumerate(fits_files, start=1):
        relative_path = input_file.relative_to(input_path)
        output_file = output_path / relative_path

        trim_one_fits_file(
            input_file=input_file,
            output_file=output_file,
            x0=x0,
            x1=x1,
            y0=y0,
            y1=y1,
            skip_existing=skip_existing)

        if progress_callback is not None:
            progress_callback(
                i,
                len(fits_files),
                f"Running Trim : {Path(input_file).name}")

    return {
        "n_files": len(fits_files),
        "target_width": int(target_width),
        "target_height": int(target_height),
        "use_common_min_size": use_common_min_size,
        "min_width": int(min_width),
        "min_height": int(min_height),
        "max_width": int(max_width),
        "max_height": int(max_height),
        "trim_box": {
            "x0": int(x0),
            "x1": int(x1),
            "y0": int(y0),
            "y1": int(y1),
        },
        "message": "Center trim finished"}