from pathlib import Path
from astropy.io import fits
import numpy as np
from scipy.ndimage import shift as image_shift


def load_fits_float32(file_path):
    data, header = fits.getdata(file_path, header=True, memmap=True)
    data = np.asarray(data, dtype=np.float32)
    return data, header


def find_centroid_in_box(data, x_guess, y_guess, box_size=40):
    half = box_size // 2

    x_guess = int(round(x_guess))
    y_guess = int(round(y_guess))

    y_min = max(y_guess - half, 0)
    y_max = min(y_guess + half, data.shape[0])

    x_min = max(x_guess - half, 0)
    x_max = min(x_guess + half, data.shape[1])

    cutout = data[y_min:y_max, x_min:x_max].astype(np.float32)

    if cutout.size == 0:
        raise ValueError("Cutout is empty. Check x_guess/y_guess or box_size.")

    background = np.nanmedian(cutout)
    signal = cutout - background

    signal[signal < 0] = 0

    total = np.nansum(signal)

    if total <= 0:
        raise ValueError("Cannot find centroid. Signal is too weak or box is wrong.")

    yy, xx = np.indices(signal.shape)

    x_centroid_local = np.nansum(xx * signal) / total
    y_centroid_local = np.nansum(yy * signal) / total

    x_centroid = x_min + x_centroid_local
    y_centroid = y_min + y_centroid_local

    return float(x_centroid), float(y_centroid)


def align_one_file_by_centroid(
    input_file,
    output_file,
    x_reference,
    y_reference,
    x_guess,
    y_guess,
    box_size=40,
    skip_existing=False
):
    
    input_file = Path(input_file)
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if skip_existing and output_file.exists():
        print(f"Skip aligned existing: {output_file.name}")
        return

    print(f"Aligning: {input_file.name}")

    data, header = load_fits_float32(input_file)

    x_centroid, y_centroid = find_centroid_in_box(
        data=data,
        x_guess=x_guess,
        y_guess=y_guess,
        box_size=box_size
    )

    dx = x_reference - x_centroid
    dy = y_reference - y_centroid

    aligned_data = image_shift(
        data,
        shift=(dy, dx),
        order=1,
        mode="nearest",
        prefilter=False
    ).astype(np.float32)

    header["HISTORY"] = "Aligned by centroid-based shift"
    header["XREF"] = float(x_reference)
    header["YREF"] = float(y_reference)
    header["XCEN"] = float(x_centroid)
    header["YCEN"] = float(y_centroid)
    header["SHIFTX"] = float(dx)
    header["SHIFTY"] = float(dy)
    header["BZERO"] = 0
    header["BSCALE"] = 1

    fits.writeto(
        output_file,
        aligned_data,
        header=header,
        overwrite=True
    )

    del data
    del aligned_data


def run_centroid_alignment(
    input_path,
    output_path,
    x_star,
    y_star,
    box_size=40,
    skip_existing=False,
    progress_callback=None,
):
    
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    fits_files = sorted(
        list(input_path.rglob("*.fits")) +
        list(input_path.rglob("*.fit")) +
        list(input_path.rglob("*.fts"))
    )

    print("\n========== CENTROID ALIGNMENT ==========")
    print("Input :", input_path)
    print("Output:", output_path)
    print("Number of files:", len(fits_files))

    if len(fits_files) == 0:
        print("No files found for alignment")
        return

    reference_file = fits_files[0]
    print("Reference file:", reference_file)

    reference_data, _ = load_fits_float32(reference_file)

    x_reference, y_reference = find_centroid_in_box(
        data=reference_data,
        x_guess=x_star,
        y_guess=y_star,
        box_size=box_size
    )

    print("Reference centroid:")
    print("x =", x_reference)
    print("y =", y_reference)

    del reference_data

    x_guess = x_reference
    y_guess = y_reference

    for i, input_file in enumerate(fits_files, start=1):
        relative_path = input_file.relative_to(input_path)
        output_file = output_path / relative_path

        print(f"\n[ALIGN {i}/{len(fits_files)}]")

        try:
            data, _ = load_fits_float32(input_file)

            x_centroid, y_centroid = find_centroid_in_box(
                data=data,
                x_guess=x_guess,
                y_guess=y_guess,
                box_size=box_size
            )

            del data

            align_one_file_by_centroid(
                input_file=input_file,
                output_file=output_file,
                x_reference=x_reference,
                y_reference=y_reference,
                x_guess=x_guess,
                y_guess=y_guess,
                box_size=box_size,
                skip_existing=skip_existing
            )

            x_guess = x_centroid
            y_guess = y_centroid

        except Exception as e:
            print("Alignment failed:", input_file)
            print("Reason:", e)

        if progress_callback is not None:
            progress_callback(
            i,
            len(fits_files),
            f"Aligning {Path(input_file).name}",
        )

    print("\nCentroid alignment finished")