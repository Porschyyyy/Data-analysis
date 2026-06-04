from pathlib import Path
from astropy.io import fits
import numpy as np


def read_fits_data(file_path):
    data = fits.getdata(file_path, memmap=False)
    data = np.asarray(data, dtype=np.float32)

    return data


def overscan_correct(data, overscan_slice=None):
    if overscan_slice is None:
        return data

    overscan_region = data[overscan_slice]
    overscan_level = np.nanmedian(overscan_region)
    corrected = data - overscan_level

    return corrected


def trim_image(data, trim_slice=None):
    if trim_slice is None:
        return data
    
    return data[trim_slice]


def preprocess_image(file_path, overscan_slice=None, trim_slice=None):
    data = read_fits_data(file_path)
    data = overscan_correct(data, overscan_slice=overscan_slice)
    data = trim_image(data, trim_slice=trim_slice)

    return data.astype(np.float32)


def combine_median(files, overscan_slice=None, trim_slice=None):
    stack = []

    for file_path in files:
        data = preprocess_image(
            file_path,
            overscan_slice=overscan_slice,
            trim_slice=trim_slice)

        stack.append(data)

    stack = np.asarray(stack, dtype=np.float32)
    master = np.nanmedian(stack, axis=0).astype(np.float32)

    del stack
    return master


def combine_mean_streaming(files, overscan_slice=None, trim_slice=None):
    sum_image = None
    count = 0

    for file_path in files:
        data = preprocess_image(
            file_path,
            overscan_slice=overscan_slice,
            trim_slice=trim_slice)

        if sum_image is None:
            sum_image = np.zeros_like(data, dtype=np.float32)

        sum_image += data
        count += 1

        del data

    if count == 0:
        return None

    master = (sum_image / count).astype(np.float32)

    return master


def save_fits_image(data, output_file, header=None):
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    data = np.asarray(data, dtype=np.float32)

    if header is None:
        header = fits.Header()

    header["BZERO"] = 0
    header["BSCALE"] = 1
    header["HISTORY"] = "Calibrated with Python/Astropy"
    header["HISTORY"] = "Saved as float32 FITS image"

    hdu = fits.PrimaryHDU(data=data, header=header)
    hdu.writeto(output_file, overwrite=True)

    print("Saved:", output_file)
    

# Create master bias from bias frames
def create_master_bias(
    bias_files,
    output_file,
    overscan_slice=None,
    trim_slice=None,
    combine_method="median",
    skip_existing=False,
    progress_callback=None):

    output_file = Path(output_file)

    if skip_existing and output_file.exists():
        print("Skip existing master bias:", output_file)
        return read_fits_data(output_file)


    if len(bias_files) == 0:
        print("No bias files found")
        return None

    stack = []
    sum_image = None
    count = 0

    for i, file_path in enumerate(bias_files, start=1):
        data = preprocess_image(
            file_path,
            overscan_slice=overscan_slice,
            trim_slice=trim_slice)

        if progress_callback is not None:
            progress_callback(
                i,
                len(bias_files),
                f"Creating master bias {i}/{len(bias_files)}: {Path(file_path).name}")

        if combine_method == "median":
            stack.append(data.astype(np.float32))

        elif combine_method == "mean":
            if sum_image is None:
                sum_image = np.zeros_like(data, dtype=np.float64)

            sum_image += data
            count += 1

        else:
            raise ValueError("combine_method must be 'median' or 'mean'")

    if combine_method == "median":
        master_bias = np.nanmedian(
            np.asarray(stack, dtype=np.float32),
            axis=0,
        ).astype(np.float32)

    elif combine_method == "mean":
        master_bias = (sum_image / count).astype(np.float32)
    else:
        raise ValueError("combine_method must be 'median' or 'mean'")

    header = fits.Header()
    header["IMAGETYP"] = "MASTER_BIAS"
    header["NCOMBINE"] = len(bias_files)
    header["COMBINE"] = combine_method

    save_fits_image(master_bias, output_file, header=header)
    return master_bias


# Create master dark after bias subtraction
def create_master_dark(
    dark_files,
    output_file,
    master_bias=None,
    overscan_slice=None,
    trim_slice=None,
    combine_method="median",
    skip_existing=False,
    progress_callback=None):

    output_file = Path(output_file)

    if skip_existing and output_file.exists():
        print("Skip existing master dark:", output_file)
        return read_fits_data(output_file)

    if len(dark_files) == 0:
        print("No dark files found")
        return None

    calibrated_stack = []

    if combine_method == "median":
        for i, file_path in enumerate(dark_files, start=1):
            data = preprocess_image(
                file_path,
                overscan_slice=overscan_slice,
                trim_slice=trim_slice)

            if master_bias is not None:
                data = data - master_bias

            if progress_callback is not None:
                progress_callback(
                    i,
                    len(dark_files),
                    f"Creating master dark {i}/{len(dark_files)}: {Path(file_path).name}")

            calibrated_stack.append(data.astype(np.float32))

        calibrated_stack = np.asarray(calibrated_stack, dtype=np.float32)
        master_dark = np.nanmedian(calibrated_stack, axis=0).astype(np.float32)

        del calibrated_stack

    elif combine_method == "mean":
        sum_image = None
        count = 0

        for i, file_path in enumerate(dark_files, start=1):
            data = preprocess_image(
                file_path,
                overscan_slice=overscan_slice,
                trim_slice=trim_slice)

            if master_bias is not None:
                data = data - master_bias

            if progress_callback is not None:
                progress_callback(
                    i,
                    len(dark_files),
                    f"Creating master dark {i}/{len(dark_files)}: {Path(file_path).name}")

            if sum_image is None:
                sum_image = np.zeros_like(data, dtype=np.float32)

            sum_image += data
            count += 1

            del data

        master_dark = (sum_image / count).astype(np.float32)

    else:
        raise ValueError("combine_method must be 'median' or 'mean'")

    header = fits.Header()
    header["IMAGETYP"] = "MASTER_DARK"
    header["NCOMBINE"] = len(dark_files)
    header["COMBINE"] = combine_method

    save_fits_image(master_dark, output_file, header=header)
    return master_dark


# Create normalized master flat
def create_master_flat(
    flat_files,
    output_file,
    master_bias=None,
    master_dark=None,
    overscan_slice=None,
    trim_slice=None,
    combine_method="median",
    skip_existing=False,
    progress_callback=None):

    output_file = Path(output_file)

    if skip_existing and output_file.exists():
        print("Skip existing master flat:", output_file)
        return read_fits_data(output_file)

    if len(flat_files) == 0:
        print("No flat files found")
        return None

    calibrated_stack = []

    if combine_method == "median":
        for i, file_path in enumerate(flat_files, start=1):
            data = preprocess_image(
                file_path,
                overscan_slice=overscan_slice,
                trim_slice=trim_slice)

            if master_bias is not None:
                data = data - master_bias

            if master_dark is not None:
                data = data - master_dark

            median_value = np.nanmedian(data)

            if median_value != 0:
                data = data / median_value

            if progress_callback is not None:
                progress_callback(
                    i,
                    len(flat_files),
                    f"Creating master flat {i}/{len(flat_files)}: {Path(file_path).name}")

            calibrated_stack.append(data.astype(np.float32))

        calibrated_stack = np.asarray(calibrated_stack, dtype=np.float32)
        master_flat = np.nanmedian(calibrated_stack, axis=0).astype(np.float32)

        del calibrated_stack

    elif combine_method == "mean":
        sum_image = None
        count = 0

        for i, file_path in enumerate(flat_files, start=1):
            data = preprocess_image(
                file_path,
                overscan_slice=overscan_slice,
                trim_slice=trim_slice)

            if master_bias is not None:
                data = data - master_bias

            if master_dark is not None:
                data = data - master_dark

            median_value = np.nanmedian(data)

            if median_value != 0:
                data = data / median_value

            if progress_callback is not None:
                progress_callback(
                    i,
                    len(flat_files),
                    f"Creating master flat {i}/{len(flat_files)}: {Path(file_path).name}")

            if sum_image is None:
                sum_image = np.zeros_like(data, dtype=np.float32)

            sum_image += data
            count += 1

            del data

        master_flat = (sum_image / count).astype(np.float32)

    else:
        raise ValueError("combine_method must be 'median' or 'mean'")

    norm = np.nanmedian(master_flat)

    if norm != 0:
        master_flat = master_flat / norm

    header = fits.Header()
    header["IMAGETYP"] = "MASTER_FLAT"
    header["NCOMBINE"] = len(flat_files)
    header["COMBINE"] = combine_method

    save_fits_image(master_flat, output_file, header=header)

    return master_flat.astype(np.float32)


def load_master(master_file):
    if master_file is None:
        return None

    data = fits.getdata(master_file, memmap=True)
    data = np.asarray(data, dtype=np.float32)

    return data


# Calibrate science frames using master bias, dark, and flat
def calibrate_light_frame(
    light_file,
    output_file,
    master_bias_file=None,
    master_dark_file=None,
    master_flat_file=None,
    overscan_slice=None,
    trim_slice=None):
    

    light_file = Path(light_file)
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    data = preprocess_image(
        light_file,
        overscan_slice=overscan_slice,
        trim_slice=trim_slice)

    hdr = fits.getheader(light_file)

    master_bias = load_master(master_bias_file)
    master_dark = load_master(master_dark_file)
    master_flat = load_master(master_flat_file)

    if master_bias is not None:
        data = data - master_bias

    if master_dark is not None:
        data = data - master_dark

    if master_flat is not None:
        safe_flat = np.asarray(master_flat, dtype=np.float32)
        safe_flat = np.where(np.isfinite(safe_flat) & (safe_flat > 0), safe_flat, np.nan)
        data = data / safe_flat
        data = np.where(np.isfinite(data), data, np.nan).astype(np.float32)

    data = data.astype(np.float32)

    hdr["IMAGETYP"] = "CALIBRATED"
    hdr["CALSTAT"] = "BDF"
    hdr["HISTORY"] = "Overscan/trim applied if configured"
    hdr["HISTORY"] = "Bias subtracted"
    hdr["HISTORY"] = "Dark subtracted"
    hdr["HISTORY"] = "Flat corrected"
    hdr["BZERO"] = 0
    hdr["BSCALE"] = 1

    fits.writeto(
        output_file,
        data,
        header=hdr,
        overwrite=True)

    del data
    del master_bias
    del master_dark
    del master_flat


def calibrate_light_files(
    light_files,
    output_dir,
    master_bias_file=None,
    master_dark_file=None,
    master_flat_file=None,
    overscan_slice=None,
    trim_slice=None,
    skip_existing=False,
    progress_callback=None,
    progress_start=0,
    progress_total=None,):
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, light_file in enumerate(light_files, start=1):
        light_file = Path(light_file)
        output_file = output_dir / f"cal_{light_file.name}"

        if skip_existing and output_file.exists():
            print(f"[CALIBRATE {i}/{len(light_files)}] Skip existing: {output_file.name}")
            continue

        calibrate_light_frame(
            light_file=light_file,
            output_file=output_file,
            master_bias_file=master_bias_file,
            master_dark_file=master_dark_file,
            master_flat_file=master_flat_file,
            overscan_slice=overscan_slice,
            trim_slice=trim_slice)

        if progress_callback is not None:
            current = progress_start + i
            total = progress_total or len(light_files)
            progress_callback(
                current,
                total,
                f"Calibrating {Path(light_file).name}")