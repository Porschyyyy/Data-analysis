from pathlib import Path
from astropy.io import fits
from astropy.time import Time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from photutils.aperture import (
    CircularAperture,
    CircularAnnulus,
    aperture_photometry,
)


def get_fits_files(input_path):
    input_path = Path(input_path)

    return sorted(
        list(input_path.rglob("*.fits")) +
        list(input_path.rglob("*.fit")) +
        list(input_path.rglob("*.fts"))
    )


def is_science_fits_file(file_path):
    name = Path(file_path).name.lower()

    bad_keywords = [
        "bias",
        "dark",
        "flat",
        "master",
    ]

    for key in bad_keywords:
        if key in name:
            return False

    return True


def filter_science_fits_files(fits_files):
    science_files = []
    skipped_files = []

    for f in fits_files:
        if is_science_fits_file(f):
            science_files.append(f)
        else:
            skipped_files.append(f)

    print("\n========== SCIENCE FILE FILTER ==========")
    print("Science files:", len(science_files))
    print("Skipped calibration files:", len(skipped_files))

    if len(skipped_files) > 0:
        print("Examples skipped:")
        for f in skipped_files[:10]:
            print("-", Path(f).name)

    return science_files


def get_time_from_header(header):
    for key in ["BJD_TDB", "BJD", "JD", "HJD"]:
        value = header.get(key)

        if value is not None:
            try:
                return float(value), key
            except Exception:
                pass

    mjd = header.get("MJD-OBS")

    if mjd is not None:
        try:
            return float(mjd), "MJD-OBS"
        except Exception:
            pass

    date_obs = header.get("DATE-OBS")

    if date_obs is not None:
        try:
            try:
                t = Time(date_obs, format="isot", scale="utc")
            except Exception:
                t = Time(date_obs, scale="utc")

            return float(t.jd), "DATE-OBS_TO_JD"
        except Exception:
            pass

    return np.nan, "UNKNOWN"


def make_odd(value):
    value = int(round(value))

    if value % 2 == 0:
        value += 1

    return value


def find_centroid_in_box(data, x_guess, y_guess, box_size=25):
    half = int(box_size) // 2

    x_guess_int = int(round(x_guess))
    y_guess_int = int(round(y_guess))

    y_min = max(y_guess_int - half, 0)
    y_max = min(y_guess_int + half + 1, data.shape[0])

    x_min = max(x_guess_int - half, 0)
    x_max = min(x_guess_int + half + 1, data.shape[1])

    cutout = data[y_min:y_max, x_min:x_max].astype(np.float64)

    if cutout.size == 0:
        return float(x_guess), float(y_guess)

    # ลบ background
    background = np.nanmedian(cutout)
    signal = cutout - background
    signal[~np.isfinite(signal)] = 0
    signal[signal < 0] = 0

    # ถ้าสัญญาณอ่อนมาก ให้ใช้ตำแหน่งเดิม
    if np.nansum(signal) <= 0:
        return float(x_guess), float(y_guess)

    # หา pixel ที่สว่างสุดในกล่อง
    peak_y, peak_x = np.unravel_index(
        np.nanargmax(signal),
        signal.shape,
    )

    # คำนวณ centroid เฉพาะบริเวณรอบ peak
    small_half = max(4, int(box_size // 6))

    py_min = max(peak_y - small_half, 0)
    py_max = min(peak_y + small_half + 1, signal.shape[0])

    px_min = max(peak_x - small_half, 0)
    px_max = min(peak_x + small_half + 1, signal.shape[1])

    small_signal = signal[py_min:py_max, px_min:px_max]

    total = np.nansum(small_signal)

    if not np.isfinite(total) or total <= 0:
        return float(x_guess), float(y_guess)

    yy, xx = np.indices(small_signal.shape)

    x_centroid_local = np.nansum(xx * small_signal) / total
    y_centroid_local = np.nansum(yy * small_signal) / total

    x_centroid = x_min + px_min + x_centroid_local
    y_centroid = y_min + py_min + y_centroid_local

    return float(x_centroid), float(y_centroid)


def recenter_positions(data, positions, centroid_box_size=25):
    new_positions = []

    for x, y in positions:
        x_new, y_new = find_centroid_in_box(
            data=data,
            x_guess=x,
            y_guess=y,
            box_size=centroid_box_size,
        )

        new_positions.append((x_new, y_new))

    return new_positions


def estimate_fwhm_one_star(data, x, y, box_size=35):
    half = int(box_size) // 2

    x = int(round(x))
    y = int(round(y))

    y_min = max(y - half, 0)
    y_max = min(y + half + 1, data.shape[0])

    x_min = max(x - half, 0)
    x_max = min(x + half + 1, data.shape[1])

    cutout = data[y_min:y_max, x_min:x_max].astype(np.float64)

    if cutout.size == 0:
        return np.nan

    background = np.nanmedian(cutout)

    signal = cutout - background
    signal[signal < 0] = 0

    total = np.nansum(signal)

    if not np.isfinite(total) or total <= 0:
        return np.nan

    yy, xx = np.indices(signal.shape)

    x_cent = np.nansum(xx * signal) / total
    y_cent = np.nansum(yy * signal) / total

    r2 = (xx - x_cent) ** 2 + (yy - y_cent) ** 2

    sigma2 = np.nansum(r2 * signal) / total / 2.0

    if not np.isfinite(sigma2) or sigma2 <= 0:
        return np.nan

    sigma = np.sqrt(sigma2)

    fwhm = 2.355 * sigma

    return float(fwhm)


def estimate_fwhm_from_image(data, positions, centroid_box_size=25):
    measured_positions = recenter_positions(
        data=data,
        positions=positions,
        centroid_box_size=centroid_box_size,
    )

    fwhm_values = []

    for x, y in measured_positions:
        fwhm = estimate_fwhm_one_star(
            data=data,
            x=x,
            y=y,
            box_size=35,
        )

        # กรองค่าที่เพี้ยนเกินไป
        if np.isfinite(fwhm) and 1.0 <= fwhm <= 30.0:
            fwhm_values.append(fwhm)

    if len(fwhm_values) == 0:
        return np.nan

    return float(np.nanmedian(fwhm_values))


def auto_photometry_params_from_files(
    fits_files,
    positions,
    sample_size=10,
):

    fwhm_list = []

    sample_files = fits_files[:sample_size]

    print("\n========== AUTO PHOTOMETRY PARAMS ==========")
    print("Estimating FWHM from", len(sample_files), "files")

    for input_file in sample_files:
        try:
            data, _ = fits.getdata(input_file, header=True, memmap=True)
            data = np.asarray(data, dtype=np.float32)

            fwhm = estimate_fwhm_from_image(
                data=data,
                positions=positions,
                centroid_box_size=25,
            )

            if np.isfinite(fwhm):
                fwhm_list.append(fwhm)
                print(input_file.name, "FWHM =", round(fwhm, 2))
            else:
                print(input_file.name, "FWHM = nan")

            del data

        except Exception as e:
            print("Estimate FWHM failed:", input_file.name)
            print("Reason:", e)

    if len(fwhm_list) == 0:
        print("Cannot estimate FWHM. Use default values.")

        return {
            "fwhm": np.nan,
            "aperture_radius": 10,
            "annulus_inner": 20,
            "annulus_outer": 35,
            "centroid_box_size": 25,
        }

    median_fwhm = float(np.nanmedian(fwhm_list))

    aperture_radius = max(5, int(round(1.8 * median_fwhm)))
    annulus_inner = max(aperture_radius + 5, int(round(3.0 * median_fwhm)))
    annulus_outer = max(annulus_inner + 8, int(round(5.0 * median_fwhm)))
    centroid_box_size = max(15, make_odd(6.0 * median_fwhm))

    print("\nMedian FWHM =", round(median_fwhm, 2))
    print("Auto aperture_radius =", aperture_radius)
    print("Auto annulus_inner =", annulus_inner)
    print("Auto annulus_outer =", annulus_outer)
    print("Auto centroid_box_size =", centroid_box_size)

    return {
        "fwhm": median_fwhm,
        "aperture_radius": aperture_radius,
        "annulus_inner": annulus_inner,
        "annulus_outer": annulus_outer,
        "centroid_box_size": centroid_box_size,
    }


def flux_to_inst_mag(flux):
    if np.isfinite(flux) and flux > 0:
        return float(-2.5 * np.log10(flux))
    return np.nan



def measure_aperture_photometry_one_file(
    input_file,
    positions,
    aperture_radius=10,
    annulus_inner=20,
    annulus_outer=35,
    centroid_box_size=25,
    recenter=True,
    estimated_fwhm=np.nan,
):
    input_file = Path(input_file)

    data, header = fits.getdata(input_file, header=True, memmap=True)
    data = np.asarray(data, dtype=np.float32)

    if recenter:
        measured_positions = recenter_positions(
            data=data,
            positions=positions,
            centroid_box_size=centroid_box_size,
        )
    else:
        measured_positions = positions

    apertures = CircularAperture(
        measured_positions,
        r=aperture_radius,
    )

    annuli = CircularAnnulus(
        measured_positions,
        r_in=annulus_inner,
        r_out=annulus_outer,
    )

    aperture_table = aperture_photometry(data, apertures)

    aperture_sums = np.array(
        aperture_table["aperture_sum"],
        dtype=np.float64,
    )

    annulus_masks = annuli.to_mask(method="center")

    background_medians = []

    for mask in annulus_masks:
        annulus_data = mask.multiply(data)

        annulus_values = annulus_data[mask.data > 0]
        annulus_values = annulus_values[np.isfinite(annulus_values)]

        if len(annulus_values) == 0:
            background_medians.append(np.nan)
        else:
            background_medians.append(np.nanmedian(annulus_values))

    background_medians = np.array(background_medians, dtype=np.float64)

    aperture_area = apertures.area

    net_fluxes = aperture_sums - background_medians * aperture_area

    time_value, time_type = get_time_from_header(header)

    row = {
        "file": str(input_file),
        "filename": input_file.name,
        "time": time_value,
        "time_type": time_type,
        "estimated_fwhm": estimated_fwhm,
        "aperture_radius": aperture_radius,
        "annulus_inner": annulus_inner,
        "annulus_outer": annulus_outer,
        "centroid_box_size": centroid_box_size,
        "recenter": recenter,
    }

    # target = star 0
    row["target_flux"] = net_fluxes[0]
    row["target_inst_mag"] = flux_to_inst_mag(net_fluxes[0])
    row["target_bkg_median"] = background_medians[0]
    row["target_x"] = measured_positions[0][0]
    row["target_y"] = measured_positions[0][1]

    # comparison stars = star 1 เป็นต้นไป
    comp_fluxes = []

    for i in range(1, len(measured_positions)):
        comp_name = f"comp{i}"

        row[f"{comp_name}_flux"] = net_fluxes[i]
        row[f"{comp_name}_inst_mag"] = flux_to_inst_mag(net_fluxes[i])
        row[f"{comp_name}_bkg_median"] = background_medians[i]
        row[f"{comp_name}_x"] = measured_positions[i][0]
        row[f"{comp_name}_y"] = measured_positions[i][1]

        comp_fluxes.append(net_fluxes[i])

    comp_fluxes = np.array(comp_fluxes, dtype=np.float64)

    # ใช้เฉพาะ comparison star ที่ flux เป็นบวกและไม่ใช่ nan
    good_comp = np.isfinite(comp_fluxes) & (comp_fluxes > 0)

    comp_sum = np.nansum(comp_fluxes[good_comp])

    row["comparison_flux_sum"] = comp_sum
    row["n_good_comparison"] = int(np.sum(good_comp))

    target_ok = np.isfinite(net_fluxes[0]) and net_fluxes[0] > 0
    comp_ok = np.isfinite(comp_sum) and comp_sum > 0
    n_comp_ok = int(np.sum(good_comp))

    row["quality_flag"] = "ok"

    if not target_ok:
        row["quality_flag"] = "bad_target_flux"

    elif not comp_ok:
        row["quality_flag"] = "bad_comparison_flux"

    elif n_comp_ok < 1:
        row["quality_flag"] = "no_good_comparison"

    if target_ok and comp_ok and n_comp_ok >= 1:
        row["relative_flux"] = net_fluxes[0] / comp_sum
    else:
        row["relative_flux"] = np.nan

    del data

    return row


def plot_photometry_debug(df, output_csv):
    output_csv = Path(output_csv)
    debug_dir = output_csv.parent / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    if len(df) == 0:
        return

    x = np.arange(len(df))

    # 1) target vs comparison flux
    plt.figure(figsize=(10, 5))

    if "target_flux" in df.columns:
        target = pd.to_numeric(df["target_flux"], errors="coerce")
        target_norm = target / np.nanmedian(target)
        plt.plot(x, target_norm, label="target_flux / median")

    if "comparison_flux_sum" in df.columns:
        comp = pd.to_numeric(df["comparison_flux_sum"], errors="coerce")
        comp_norm = comp / np.nanmedian(comp)
        plt.plot(x, comp_norm, label="comparison_flux_sum / median")

    if "weighted_comparison_flux_sum" in df.columns:
        wcomp = pd.to_numeric(df["weighted_comparison_flux_sum"], errors="coerce")
        wcomp_norm = wcomp / np.nanmedian(wcomp)
        plt.plot(x, wcomp_norm, label="weighted_comparison_flux_sum / median")

    plt.xlabel("Frame index")
    plt.ylabel("Normalized flux")
    plt.title("Debug: Target vs Comparison Flux")
    plt.legend()
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(debug_dir / "debug_target_vs_comparison.png", dpi=200)
    plt.close()

    # 2) each comparison star
    comp_cols = [
        col for col in df.columns
        if col.startswith("comp") and col.endswith("_flux")
    ]

    if len(comp_cols) > 0:
        plt.figure(figsize=(10, 5))

        for col in comp_cols:
            values = pd.to_numeric(df[col], errors="coerce")
            med = np.nanmedian(values)

            if np.isfinite(med) and med != 0:
                plt.plot(x, values / med, label=f"{col} / median")

        plt.xlabel("Frame index")
        plt.ylabel("Normalized flux")
        plt.title("Debug: Each Comparison Star")
        plt.legend()
        plt.grid(True, alpha=0.25)
        plt.tight_layout()
        plt.savefig(debug_dir / "debug_each_comparison_star.png", dpi=200)
        plt.close()

    # 3) relative flux
    if "relative_flux" in df.columns:
        plt.figure(figsize=(10, 5))
        rel = pd.to_numeric(df["relative_flux"], errors="coerce")
        plt.plot(x, rel, marker="o", linestyle="none", markersize=3)
        plt.xlabel("Frame index")
        plt.ylabel("Relative flux")
        plt.title("Debug: Relative Flux")
        plt.grid(True, alpha=0.25)
        plt.tight_layout()
        plt.savefig(debug_dir / "debug_relative_flux.png", dpi=200)
        plt.close()

    print("Saved photometry debug plots:", debug_dir)


def compute_flux_rms_ppm(flux):
    flux = np.asarray(flux, dtype=float)
    flux = flux[np.isfinite(flux)]

    if len(flux) == 0:
        return np.nan

    norm = flux / np.nanmedian(flux)
    rms = np.nanstd(norm - 1.0)

    return float(rms * 1e6)


def optimize_aperture_radius(
    fits_files,
    positions,
    estimated_fwhm,
    centroid_box_size,
    recenter=True,
):
    
    if not np.isfinite(estimated_fwhm):
        candidate_radii = [6, 8, 10, 12, 14]
    else:
        base = float(estimated_fwhm)
        candidate_radii = [
            max(4, round(1.2 * base)),
            max(5, round(1.5 * base)),
            max(6, round(1.8 * base)),
            max(7, round(2.1 * base)),
            max(8, round(2.5 * base)),
        ]

    candidate_radii = sorted(set(int(r) for r in candidate_radii))

    sample_files = fits_files[:min(30, len(fits_files))]

    results = []

    print("\n========== APERTURE OPTIMIZATION ==========")

    for aperture_radius in candidate_radii:
        annulus_inner = max(aperture_radius + 5, int(round(aperture_radius * 1.8)))
        annulus_outer = max(annulus_inner + 8, int(round(aperture_radius * 2.8)))

        relative_fluxes = []

        for input_file in sample_files:
            try:
                row = measure_aperture_photometry_one_file(
                    input_file=input_file,
                    positions=positions,
                    aperture_radius=aperture_radius,
                    annulus_inner=annulus_inner,
                    annulus_outer=annulus_outer,
                    centroid_box_size=centroid_box_size,
                    recenter=recenter,
                    estimated_fwhm=estimated_fwhm,
                )

                relative_fluxes.append(row["relative_flux"])

            except Exception:
                pass

        rms_ppm = compute_flux_rms_ppm(relative_fluxes)

        results.append({
            "aperture_radius": aperture_radius,
            "annulus_inner": annulus_inner,
            "annulus_outer": annulus_outer,
            "rms_ppm": rms_ppm,
        })

        print(
            f"r={aperture_radius}, "
            f"annulus={annulus_inner}-{annulus_outer}, "
            f"RMS={rms_ppm:.0f} ppm"
        )

    valid = [r for r in results if np.isfinite(r["rms_ppm"])]

    if len(valid) == 0:
        print("Aperture optimization failed. Use default values.")
        return None

    best = min(valid, key=lambda item: item["rms_ppm"])

    print("\nBest aperture:")
    print(best)

    return best


def compute_comparison_weights(df):
    comp_cols = [
        col for col in df.columns
        if col.startswith("comp") and col.endswith("_flux")
    ]

    weights = {}

    for col in comp_cols:
        flux = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
        flux = flux[np.isfinite(flux) & (flux > 0)]

        if len(flux) < 5:
            weights[col] = 0.0
            continue

        norm_flux = flux / np.nanmedian(flux)
        scatter = np.nanstd(norm_flux - 1.0)

        if not np.isfinite(scatter) or scatter <= 0:
            weights[col] = 0.0
        else:
            weights[col] = 1.0 / (scatter ** 2)

    total_weight = sum(weights.values())

    if total_weight <= 0:
        n = len(comp_cols)
        if n == 0:
            return {}

        return {col: 1.0 / n for col in comp_cols}

    return {
        col: weight / total_weight
        for col, weight in weights.items()
    }


def apply_weighted_comparison(df):
    comp_cols = [
        col for col in df.columns
        if col.startswith("comp") and col.endswith("_flux")
    ]

    if len(comp_cols) == 0:
        df["weighted_comparison_flux_sum"] = np.nan
        df["weighted_relative_flux"] = np.nan
        return df, {}

    weights = compute_comparison_weights(df)

    weighted_sum = np.zeros(len(df), dtype=float)

    for col in comp_cols:
        flux = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
        weight = weights.get(col, 0.0)

        weighted_sum += weight * flux

        df[col.replace("_flux", "_weight")] = weight

    df["weighted_comparison_flux_sum"] = weighted_sum

    target_flux = pd.to_numeric(df["target_flux"], errors="coerce").to_numpy(dtype=float)

    good = (
        np.isfinite(target_flux)
        & np.isfinite(weighted_sum)
        & (target_flux > 0)
        & (weighted_sum > 0)
    )

    df["weighted_relative_flux"] = np.nan
    df.loc[good, "weighted_relative_flux"] = target_flux[good] / weighted_sum[good]

    return df, weights


def save_photometry_quality_summary(df, output_csv):
    output_csv = Path(output_csv)
    summary_csv = output_csv.parent / "photometry_quality_summary.csv"

    summary = {}

    summary["n_frames"] = len(df)

    if "normalized_flux" in df.columns:
        flux = pd.to_numeric(df["normalized_flux"], errors="coerce")
        flux = flux[np.isfinite(flux)]

        summary["normalized_flux_median"] = float(np.nanmedian(flux))
        summary["normalized_flux_std"] = float(np.nanstd(flux))
        summary["rms_ppm"] = float(np.nanstd(flux - 1.0) * 1e6)

        summary["flux_min"] = float(np.nanmin(flux))
        summary["flux_max"] = float(np.nanmax(flux))

    if "relative_flux" in df.columns:
        rel = pd.to_numeric(df["relative_flux"], errors="coerce")
        rel = rel[np.isfinite(rel)]

        summary["relative_flux_median"] = float(np.nanmedian(rel))
        summary["relative_flux_std"] = float(np.nanstd(rel))

    if "estimated_fwhm" in df.columns:
        fwhm = pd.to_numeric(df["estimated_fwhm"], errors="coerce")
        fwhm = fwhm[np.isfinite(fwhm)]

        if len(fwhm) > 0:
            summary["estimated_fwhm_median"] = float(np.nanmedian(fwhm))

    if "aperture_radius" in df.columns:
        summary["aperture_radius"] = float(pd.to_numeric(df["aperture_radius"]).median())

    if "annulus_inner" in df.columns:
        summary["annulus_inner"] = float(pd.to_numeric(df["annulus_inner"]).median())

    if "annulus_outer" in df.columns:
        summary["annulus_outer"] = float(pd.to_numeric(df["annulus_outer"]).median())

    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(summary_csv, index=False)

    print("\nSaved photometry quality summary:")
    print(summary_csv)

    return summary_df


def run_aperture_photometry(
    input_path,
    output_csv,
    positions,
    aperture_radius=None,
    annulus_inner=None,
    annulus_outer=None,
    centroid_box_size=None,
    recenter=True,
    auto_params=True,
    progress_callback=None,
):
    input_path = Path(input_path)
    output_csv = Path(output_csv)

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    fits_files = get_fits_files(input_path)
    fits_files = filter_science_fits_files(fits_files)

    if len(fits_files) == 0:
        print("No FITS files found for photometry")
        return pd.DataFrame()


    if (
        auto_params
        or aperture_radius is None
        or annulus_inner is None
        or annulus_outer is None
        or centroid_box_size is None
    ):
        params = auto_photometry_params_from_files(
            fits_files=fits_files,
            positions=positions,
            sample_size=10,
        )

        estimated_fwhm = params["fwhm"]
        aperture_radius = params["aperture_radius"]
        annulus_inner = params["annulus_inner"]
        annulus_outer = params["annulus_outer"]
        centroid_box_size = params["centroid_box_size"]

        best_aperture = optimize_aperture_radius(
            fits_files=fits_files,
            positions=positions,
            estimated_fwhm=estimated_fwhm,
            centroid_box_size=centroid_box_size,
            recenter=recenter,
        )

        if best_aperture is not None:
            aperture_radius = best_aperture["aperture_radius"]
            annulus_inner = best_aperture["annulus_inner"]
            annulus_outer = best_aperture["annulus_outer"]

    else:
        estimated_fwhm = np.nan

    print("\n========== APERTURE PHOTOMETRY ==========")
    print("Input :", input_path)
    print("Output:", output_csv)
    print("Number of files:", len(fits_files))
    print("Number of stars:", len(positions))
    print("Estimated FWHM:", estimated_fwhm)
    print("Aperture radius:", aperture_radius)
    print("Sky annulus:", annulus_inner, "-", annulus_outer)
    print("Centroid box size:", centroid_box_size)
    print("Recenter:", recenter)

    rows = []

    for i, input_file in enumerate(fits_files, start=1):
        print(f"[PHOT {i}/{len(fits_files)}] {input_file.name}")

        try:
            row = measure_aperture_photometry_one_file(
                input_file=input_file,
                positions=positions,
                aperture_radius=aperture_radius,
                annulus_inner=annulus_inner,
                annulus_outer=annulus_outer,
                centroid_box_size=centroid_box_size,
                recenter=recenter,
                estimated_fwhm=estimated_fwhm,
            )

            rows.append(row)

        except Exception as e:
            print("Photometry failed:", input_file)
            print("Reason:", e)

        if progress_callback is not None:
            progress_callback(
            i,
            len(fits_files),
            f"Photometry {Path(input_file).name}",
        )

    df = pd.DataFrame(rows)

    if len(df) == 0:
        print("No photometry results")
        return df

    # เรียงตามเวลา
    if "time" in df.columns:
        df = df.sort_values("time").reset_index(drop=True)

    # แปลง relative_flux ให้เป็นตัวเลข
    df["relative_flux"] = pd.to_numeric(df["relative_flux"], errors="coerce")

    # ตัดค่าที่ผิดปกติแบบพื้นฐาน
    df.loc[df["relative_flux"] <= 0, "relative_flux"] = np.nan

    # ใช้ weighted comparison stars
    df, comparison_weights = apply_weighted_comparison(df)

    print("\n========== COMPARISON STAR WEIGHTS ==========")
    for name, weight in comparison_weights.items():
        print(f"{name}: {weight:.4f}")

    # ใช้ weighted_relative_flux เป็นค่า default ถ้ามี
    if "weighted_relative_flux" in df.columns:
        df["relative_flux"] = df["weighted_relative_flux"]

    # ==========================================
    # Remove bad frames automatically
    # ==========================================

    comparison_reference_col = "weighted_comparison_flux_sum"

    if comparison_reference_col not in df.columns:
        comparison_reference_col = "comparison_flux_sum"

    comparison_norm = (
        df[comparison_reference_col]
        / np.nanmedian(df[comparison_reference_col])
    )

    good_mask = comparison_norm > 0.90

    removed_frames = np.sum(~good_mask)

    print(f"\n🗑 Removed bad frames: {removed_frames}")

    df = df[good_mask].reset_index(drop=True)

    # normalize relative flux ด้วย median
    median_rel_flux = np.nanmedian(df["relative_flux"])

    if np.isfinite(median_rel_flux) and median_rel_flux != 0:
        df["normalized_flux"] = df["relative_flux"] / median_rel_flux
    else:
        df["normalized_flux"] = np.nan

    df.to_csv(output_csv, index=False)

    plot_photometry_debug(df, output_csv)
    save_photometry_quality_summary(df, output_csv)

    print("\nSaved photometry table:")
    print(output_csv)

    return df