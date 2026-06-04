from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


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

# Remove outliers using robust MAD-based sigma clipping.
# This helps reduce the impact of bad photometric measurements.
def robust_sigma_clip(y, sigma):
    y = np.asarray(y, dtype=float)

    median = np.nanmedian(y)
    mad = np.nanmedian(np.abs(y - median))

    if not np.isfinite(mad) or mad == 0:
        return np.isfinite(y)

    robust_std = 1.4826 * mad
    z = np.abs(y - median) / robust_std

    return np.isfinite(y) & (z <= sigma)


# Bin photometric measurements to reduce scatter
# and improve light curve readability.
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
        np.array(binned_flux_err))


# Compute RMS scatter in parts-per-million (ppm)
# as a basic photometric precision metric.
def compute_rms_ppm(flux):
    flux = np.asarray(flux, dtype=float)
    flux = flux[np.isfinite(flux)]

    if len(flux) == 0:
        return np.nan

    rms = np.nanstd(flux - 1.0)
    return rms * 1e6


# Estimate suitable y-axis limits for plotting.
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


# Compute moving average trend for visualization.
def moving_average(y, window=3):
    y = np.asarray(y, dtype=float)

    if window <= 1 or len(y) < window:
        return y

    return (
        pd.Series(y)
        .rolling(window=window, center=True, min_periods=1)
        .mean()
        .to_numpy())


def plot_lightcurve(
    photometry_csv: str | Path,
    output_png: str | Path,
    remove_first_point: bool = False,
    remove_outliers: bool = True,
    sigma_clip: float | None = None,
    bin_size: int | None = None,
    mid_transit_jd: float | None = None,
    transit_duration_hours: float | None = None,
    plot_style: str = "academic",
    title: str | None = None,
):
    photometry_csv = Path(photometry_csv)
    output_png = Path(output_png)

    if not photometry_csv.exists():
        raise FileNotFoundError(f"Photometry CSV not found: {photometry_csv}")

    output_png.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(photometry_csv)

    required_columns = ["time", "normalized_flux"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(
                f"Missing column '{col}' in {photometry_csv}. "
                f"Available columns: {list(df.columns)}")

    df["time"] = pd.to_numeric(df["time"], errors="coerce")
    df["normalized_flux"] = pd.to_numeric(df["normalized_flux"], errors="coerce")

    df = df.dropna(subset=["time", "normalized_flux"])
    df = df.sort_values("time").reset_index(drop=True)

    if remove_first_point and len(df) > 1:
        df = df.iloc[1:].reset_index(drop=True)

    if len(df) == 0:
        raise ValueError("No valid data left for plotting light curve.")

    first_jd = df["time"].iloc[0]
    df["time_hour"] = (df["time"] - first_jd) * 24.0

    n_points_before_clip = len(df)

    if sigma_clip is None:
        sigma_clip = choose_auto_sigma_clip(n_points_before_clip)

    if bin_size is None:
        bin_size = choose_auto_bin_size(n_points_before_clip)

    if remove_outliers:
        good_mask = robust_sigma_clip(
            df["normalized_flux"].to_numpy(),
            sigma=sigma_clip)

        df = df.loc[good_mask].reset_index(drop=True)

    if len(df) == 0:
        raise ValueError("No valid data left after outlier removal.")

    binned_time, binned_flux, binned_err = bin_lightcurve(
        time=df["time_hour"].to_numpy(),
        flux=df["normalized_flux"].to_numpy(),
        bin_size=bin_size)

    residuals = df["normalized_flux"].to_numpy() - 1.0
    binned_residuals = binned_flux - 1.0

    rms_unbinned_ppm = compute_rms_ppm(df["normalized_flux"].to_numpy())
    rms_binned_ppm = compute_rms_ppm(binned_flux)

    fig = plt.figure(figsize=(10, 6.8))

    gs = fig.add_gridspec(
        nrows=2,
        ncols=1,
        height_ratios=[3.2, 1.2],
        hspace=0.05)

    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)

    if mid_transit_jd is not None and transit_duration_hours is not None:
        x_mid_transit = (mid_transit_jd - first_jd) * 24.0
        half_dur = transit_duration_hours / 2.0
        ingress = x_mid_transit - half_dur
        egress = x_mid_transit + half_dur

        ax1.axvspan(ingress, egress, alpha=0.12)
        ax2.axvspan(ingress, egress, alpha=0.12)

        ax1.axvline(x_mid_transit, linestyle="--", linewidth=1)
        ax2.axvline(x_mid_transit, linestyle="--", linewidth=1)


    # Plot main light curve
    if plot_style == "academic":
        ax1.plot(
            df["time_hour"],
            df["normalized_flux"],
            marker="o",
            linestyle="none",
            markersize=4,
            alpha=0.35,
            label="Normalized flux")

        ax1.errorbar(
            binned_time,
            binned_flux,
            yerr=binned_err,
            marker="o",
            linestyle="-",
            linewidth=1.3,
            markersize=5,
            capsize=2,
            label=f"Binned ({bin_size} points/bin)")

    elif plot_style == "line":
        smooth_flux = moving_average(
            df["normalized_flux"].to_numpy(),
            window=3)

        ax1.plot(
            df["time_hour"],
            smooth_flux,
            linestyle="-",
            linewidth=1.5,
            alpha=0.75,
            label="Light curve")

        ax1.plot(
            binned_time,
            binned_flux,
            linestyle="-",
            linewidth=2.2,
            alpha=1.0,
            label=f"Binned light curve ({bin_size} points/bin)")

    ax1.axhline(1.0, linestyle="--", linewidth=1)

    # Plot residual panel
    if plot_style == "academic":
        ax2.plot(
            df["time_hour"],
            residuals,
            marker="o",
            linestyle="none",
            markersize=3,
            alpha=0.25)

        ax2.errorbar(
            binned_time,
            binned_residuals,
            yerr=binned_err,
            marker="o",
            linestyle="-",
            linewidth=1.0,
            markersize=4,
            capsize=2)

    elif plot_style == "line":
        smooth_residuals = moving_average(
            residuals,
            window=3)

        ax2.plot(
            df["time_hour"],
            smooth_residuals,
            linestyle="-",
            linewidth=1.0,
            alpha=0.45)

        ax2.plot(
            binned_time,
            binned_residuals,
            linestyle="-",
            linewidth=1.8,
            alpha=1.0)

    ax2.axhline(0.0, linestyle="--", linewidth=1)

    ax1.set_ylabel("Normalized Flux")
    ax2.set_ylabel("Residual")
    ax2.set_xlabel("Time from first exposure (hours)")
    ax1.set_title(title or "Light Curve")

    x_min = df["time_hour"].min()
    x_max = df["time_hour"].max()
    
    ax1.set_xlim(x_min, x_max)
    ax2.set_xlim(x_min, x_max)

    y_lim = auto_ylim(
        np.concatenate([
            df["normalized_flux"].to_numpy(),
            binned_flux,
        ]))

    if y_lim is not None:
        ax1.set_ylim(*y_lim)

    r_all = np.concatenate([residuals, binned_residuals])
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
        f"Auto binning = {bin_size} points/bin",
        f"Unbinned RMS = {rms_unbinned_ppm:.0f} ppm",
        f"Binned RMS = {rms_binned_ppm:.0f} ppm",
        f"N = {len(df)} points"]

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
        bbox=dict(boxstyle="round", alpha=0.12))

    plt.setp(ax1.get_xticklabels(), visible=False)

    fig.tight_layout()
    fig.savefig(output_png, dpi=300, bbox_inches="tight")

    plt.close(fig)

    return output_png


def plot_phase_folded_lightcurve(
    photometry_csv: str | Path,
    output_png: str | Path,
    t0: float,
    period: float,
    title: str | None = None,
):
    photometry_csv = Path(photometry_csv)
    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)

    if period <= 0:
        raise ValueError("period must be > 0")

    df = pd.read_csv(photometry_csv)

    df["time"] = pd.to_numeric(df["time"], errors="coerce")
    df["normalized_flux"] = pd.to_numeric(df["normalized_flux"], errors="coerce")
    df = df.dropna(subset=["time", "normalized_flux"])

    if len(df) == 0:
        raise ValueError("No valid data for phase-folded plot.")

    phase = ((df["time"] - t0) / period) % 1.0

    phase = np.where(phase > 0.5, phase - 1.0, phase)

    flux = df["normalized_flux"].to_numpy()

    order = np.argsort(phase)
    phase = phase[order]
    flux = flux[order]

    smooth_flux = (
        pd.Series(flux)
        .rolling(window=9, center=True, min_periods=1)
        .median()
        .to_numpy())

    plt.figure(figsize=(8, 5))

    plt.plot(
        phase,
        flux,
        marker="o",
        linestyle="none",
        markersize=3,
        alpha=0.35,
        label="Data")

    plt.plot(
        phase,
        smooth_flux,
        linestyle="-",
        linewidth=2,
        label="Smoothed trend")

    plt.axhline(1.0, linestyle="--", linewidth=1)
    plt.axvline(0.0, linestyle="--", linewidth=1)

    plt.xlabel("Orbital Phase")
    plt.ylabel("Normalized Flux")
    plt.title(title or "Phase-folded Light Curve")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_png, dpi=300, bbox_inches="tight")
    plt.close()

    return output_png
