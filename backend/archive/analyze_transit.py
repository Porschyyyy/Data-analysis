from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def ask_yes_no(prompt, default=True):
    suffix = " [Y/n]: " if default else " [y/N]: "
    value = input(prompt + suffix).strip().lower()

    if value == "":
        return default

    return value in ["y", "yes", "ใช่", "เอา"]


def ask_optional_float(prompt):
    value = input(prompt).strip()

    if value == "":
        return None

    try:
        return float(value)
    except ValueError:
        print("ค่าที่กรอกไม่ใช่ตัวเลข จะใช้ None แทน")
        return None


def compute_nearest_mid_transit(start_jd, end_jd, t0, period):
    data_mid = (start_jd + end_jd) / 2.0
    epoch = round((data_mid - t0) / period)
    mid_transit_jd = t0 + epoch * period

    return mid_transit_jd, epoch


def get_transit_info_from_data(df):
    start_jd = float(df["time"].min())
    end_jd = float(df["time"].max())
    duration_data_hours = (end_jd - start_jd) * 24.0

    print("\n========== DATA TIME RANGE ==========")
    print(f"Start JD        : {start_jd}")
    print(f"End JD          : {end_jd}")
    print(f"Data duration   : {duration_data_hours:.3f} hours")

    print("\nเลือกวิธีใส่ข้อมูล transit:")
    print("1 = ใช้ preset ของ WASP-12b แล้วคำนวณจากช่วงเวลาข้อมูล")
    print("2 = กรอก MID_TRANSIT_JD และ TRANSIT_DURATION_HOURS เอง")
    print("3 = ไม่แสดงเส้น/แถบ expected transit")

    choice = input("เลือก 1/2/3 [1]: ").strip()

    if choice == "":
        choice = "1"

    if choice == "1":
        t0 = 2454508.97682
        period = 1.09142245
        transit_duration_hours = 2.93

        mid_transit_jd, epoch = compute_nearest_mid_transit(
            start_jd=start_jd,
            end_jd=end_jd,
            t0=t0,
            period=period,
        )

        print("\n========== WASP-12b EPHEMERIS SUGGESTION ==========")
        print(f"T0               : {t0}")
        print(f"Period           : {period} days")
        print(f"Nearest epoch    : {epoch}")
        print(f"Suggested MID_TRANSIT_JD       : {mid_transit_jd}")
        print(f"Suggested TRANSIT_DURATION_HOURS: {transit_duration_hours}")

        print("\nCoverage relative to suggested mid-transit:")
        print(f"Start - mid      : {(start_jd - mid_transit_jd) * 24.0:.3f} hours")
        print(f"End - mid        : {(end_jd - mid_transit_jd) * 24.0:.3f} hours")

        use_suggested = ask_yes_no("ใช้ค่าที่คำนวณได้นี้ไหม", default=True)

        if use_suggested:
            return mid_transit_jd, transit_duration_hours

        print("\nกรอกค่าเองแทน หรือกด Enter เพื่อไม่แสดง")
        mid_transit_jd = ask_optional_float("MID_TRANSIT_JD: ")
        transit_duration_hours = ask_optional_float("TRANSIT_DURATION_HOURS: ")

        return mid_transit_jd, transit_duration_hours

    if choice == "2":
        mid_transit_jd = ask_optional_float("MID_TRANSIT_JD: ")
        transit_duration_hours = ask_optional_float("TRANSIT_DURATION_HOURS: ")

        return mid_transit_jd, transit_duration_hours

    return None, None


def choose_auto_bin_size(n_points):
    if n_points < 30:
        return 3

    if n_points < 80:
        return 4

    if n_points < 150:
        return 5

    if n_points < 300:
        return 8

    return 10


def choose_auto_sigma_clip(n_points):
    if n_points < 50:
        return 5.0

    if n_points < 150:
        return 4.0

    return 3.5


def choose_auto_detrend_degree(n_points, duration_hours):
    if n_points < 40:
        return 1

    if duration_hours < 2.0:
        return 1

    if n_points >= 60 and duration_hours >= 2.0:
        return 2

    return 1


def robust_sigma_clip(y, sigma):
    y = np.asarray(y, dtype=float)

    median = np.nanmedian(y)
    mad = np.nanmedian(np.abs(y - median))

    if not np.isfinite(mad) or mad == 0:
        return np.isfinite(y)

    robust_std = 1.4826 * mad
    z = np.abs(y - median) / robust_std

    return np.isfinite(y) & (z <= sigma)


def bin_lightcurve(time, flux, bin_size):
    time = np.asarray(time, dtype=float)
    flux = np.asarray(flux, dtype=float)

    binned_time = []
    binned_flux = []
    binned_flux_err = []

    n = len(time)

    for start in range(0, n, bin_size):
        end = start + bin_size

        t_chunk = time[start:end]
        f_chunk = flux[start:end]

        good = np.isfinite(t_chunk) & np.isfinite(f_chunk)

        if np.sum(good) == 0:
            continue

        t_good = t_chunk[good]
        f_good = f_chunk[good]

        binned_time.append(np.nanmean(t_good))
        binned_flux.append(np.nanmean(f_good))

        if len(f_good) > 1:
            binned_flux_err.append(np.nanstd(f_good, ddof=1) / np.sqrt(len(f_good)))
        else:
            binned_flux_err.append(np.nan)

    return (
        np.array(binned_time),
        np.array(binned_flux),
        np.array(binned_flux_err),
    )


def detrend_polynomial(time, flux, degree):
    time = np.asarray(time, dtype=float)
    flux = np.asarray(flux, dtype=float)

    good = np.isfinite(time) & np.isfinite(flux)

    coeff = np.polyfit(time[good], flux[good], degree)
    trend = np.polyval(coeff, time)

    detrended_flux = flux / trend
    detrended_flux = detrended_flux / np.nanmedian(detrended_flux)

    return detrended_flux, trend


def compute_rms_ppm(flux):
    flux = np.asarray(flux, dtype=float)
    flux = flux[np.isfinite(flux)]

    if len(flux) == 0:
        return np.nan

    rms = np.nanstd(flux - 1.0)
    return rms * 1e6


def auto_ylim(values, min_half_range=0.0015):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]

    if len(values) == 0:
        return None

    low = np.nanpercentile(values, 1)
    high = np.nanpercentile(values, 99)

    center = np.nanmedian(values)
    half_range = max((high - low) * 0.65, min_half_range)

    return center - half_range, center + half_range


def plot_publication_style(
    time_hour,
    flux,
    detrended_flux,
    binned_time,
    binned_flux,
    binned_err,
    output_png,
    sigma_clip,
    bin_size,
    detrend_degree,
    mid_transit_jd=None,
    first_jd=None,
    transit_duration_hours=None,
):
    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)

    residuals = detrended_flux - 1.0

    rms_unbinned_ppm = compute_rms_ppm(detrended_flux)
    rms_binned_ppm = compute_rms_ppm(binned_flux)

    fig = plt.figure(figsize=(10, 6.8))

    gs = fig.add_gridspec(
        nrows=2,
        ncols=1,
        height_ratios=[3.2, 1.2],
        hspace=0.05,
    )

    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)

    if (
        mid_transit_jd is not None
        and first_jd is not None
        and transit_duration_hours is not None
    ):
        x_mid_transit = (mid_transit_jd - first_jd) * 24.0
        half_dur = transit_duration_hours / 2.0
        ingress = x_mid_transit - half_dur
        egress = x_mid_transit + half_dur

        ax1.axvspan(ingress, egress, alpha=0.12)
        ax2.axvspan(ingress, egress, alpha=0.12)

        ax1.axvline(x_mid_transit, linestyle="--", linewidth=1)
        ax2.axvline(x_mid_transit, linestyle="--", linewidth=1)

    ax1.plot(
        time_hour,
        detrended_flux,
        marker="o",
        linestyle="none",
        markersize=4,
        alpha=0.35,
        label="Detrended flux",
    )

    ax1.errorbar(
        binned_time,
        binned_flux,
        yerr=binned_err,
        marker="o",
        linestyle="-",
        linewidth=1.3,
        markersize=5,
        capsize=2,
        label=f"Binned ({bin_size} points/bin)",
    )

    ax1.axhline(1.0, linestyle="--", linewidth=1)

    ax2.plot(
        time_hour,
        residuals,
        marker="o",
        linestyle="none",
        markersize=3,
        alpha=0.25,
    )

    ax2.errorbar(
        binned_time,
        binned_flux - 1.0,
        yerr=binned_err,
        marker="o",
        linestyle="-",
        linewidth=1.0,
        markersize=4,
        capsize=2,
    )

    ax2.axhline(0.0, linestyle="--", linewidth=1)

    ax1.set_ylabel("Normalized Flux")
    ax2.set_ylabel("Residual")
    ax2.set_xlabel("Time from first exposure (hours)")
    ax1.set_title("WASP-12b Transit Light Curve")

    y_lim = auto_ylim(
        np.concatenate([
            detrended_flux,
            binned_flux,
        ])
    )

    if y_lim is not None:
        ax1.set_ylim(*y_lim)

    r_all = np.concatenate([residuals, binned_flux - 1.0])
    r_all = r_all[np.isfinite(r_all)]

    if len(r_all) > 0:
        rmax = np.nanpercentile(np.abs(r_all), 99)
        rmax = max(rmax * 1.35, 0.0015)
        ax2.set_ylim(-rmax, rmax)

    ax1.grid(True, alpha=0.25)
    ax2.grid(True, alpha=0.25)

    ax1.legend(loc="best", fontsize=9)

    text_lines = [
        f"Auto sigma clip = {sigma_clip:.1f}",
        f"Auto detrend degree = {detrend_degree}",
        f"Auto binning = {bin_size} points/bin",
        f"Unbinned RMS = {rms_unbinned_ppm:.0f} ppm",
        f"Binned RMS = {rms_binned_ppm:.0f} ppm",
        f"N = {len(time_hour)} points",
    ]

    if mid_transit_jd is None or transit_duration_hours is None:
        text_lines.append("Expected transit: not shown")

    ax1.text(
        0.02,
        0.98,
        "\n".join(text_lines),
        transform=ax1.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox=dict(boxstyle="round", alpha=0.12),
    )

    plt.setp(ax1.get_xticklabels(), visible=False)

    fig.tight_layout()
    fig.savefig(output_png, dpi=300, bbox_inches="tight")
    plt.show()
    plt.close(fig)

    print("Saved:", output_png)


def main():
    base_dir = Path(__file__).resolve().parent
    project_dir = base_dir.parent

    photometry_csv = project_dir / "output" / "photometry" / "photometry_results.csv"

    output_dir = project_dir / "output" / "photometry" / "transit_analysis"
    output_png = output_dir / "wasp12b_publication_style.png"
    output_csv = output_dir / "transit_processed.csv"

    df = pd.read_csv(photometry_csv)

    df["time"] = pd.to_numeric(df["time"], errors="coerce")
    df["normalized_flux"] = pd.to_numeric(df["normalized_flux"], errors="coerce")

    df = df.dropna(subset=["time", "normalized_flux"])
    df = df.sort_values("time").reset_index(drop=True)

    if len(df) > 1:
        df = df.iloc[1:].reset_index(drop=True)

    first_jd = df["time"].iloc[0]
    df["time_hour"] = (df["time"] - first_jd) * 24.0

    mid_transit_jd, transit_duration_hours = get_transit_info_from_data(df)

    n_points = len(df)
    duration_hours = df["time_hour"].max() - df["time_hour"].min()

    sigma_clip = choose_auto_sigma_clip(n_points)
    bin_size = choose_auto_bin_size(n_points)
    detrend_degree = choose_auto_detrend_degree(
        n_points=n_points,
        duration_hours=duration_hours,
    )

    print("Auto sigma clip:", sigma_clip)
    print("Auto bin size:", bin_size)
    print("Auto detrend degree:", detrend_degree)

    good_mask = robust_sigma_clip(
        df["normalized_flux"].to_numpy(),
        sigma=sigma_clip,
    )

    removed = len(df) - int(np.sum(good_mask))
    print("Removed outliers:", removed)

    df = df.loc[good_mask].reset_index(drop=True)

    detrended_flux, trend = detrend_polynomial(
        time=df["time_hour"].to_numpy(),
        flux=df["normalized_flux"].to_numpy(),
        degree=detrend_degree,
    )

    df["trend"] = trend
    df["detrended_flux"] = detrended_flux

    binned_time, binned_flux, binned_err = bin_lightcurve(
        time=df["time_hour"].to_numpy(),
        flux=df["detrended_flux"].to_numpy(),
        bin_size=bin_size,
    )

    plot_publication_style(
        time_hour=df["time_hour"].to_numpy(),
        flux=df["normalized_flux"].to_numpy(),
        detrended_flux=df["detrended_flux"].to_numpy(),
        binned_time=binned_time,
        binned_flux=binned_flux,
        binned_err=binned_err,
        output_png=output_png,
        sigma_clip=sigma_clip,
        bin_size=bin_size,
        detrend_degree=detrend_degree,
        mid_transit_jd=mid_transit_jd,
        first_jd=first_jd,
        transit_duration_hours=transit_duration_hours,
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_csv, index=False)
    print("Saved:", output_csv)

    binned_df = pd.DataFrame({
        "time_hour": binned_time,
        "binned_flux": binned_flux,
        "binned_flux_err": binned_err,
    })

    binned_csv = output_dir / "transit_binned.csv"
    binned_df.to_csv(binned_csv, index=False)

    print("Saved:", binned_csv)
    print("\nDone. Check folder:")
    print(output_dir)


if __name__ == "__main__":
    main()