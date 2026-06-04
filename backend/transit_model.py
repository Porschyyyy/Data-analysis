import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import batman
from scipy.optimize import curve_fit


PERIOD_DAYS = 1.09142


def transit_model(t_day, t0, rp, a, inc):
    params = batman.TransitParams()
    params.t0 = t0
    params.per = PERIOD_DAYS
    params.rp = rp
    params.a = a
    params.inc = inc
    params.ecc = 0.0
    params.w = 90.0
    params.u = [0.3, 0.2]
    params.limb_dark = "quadratic"

    m = batman.TransitModel(params, t_day)
    return m.light_curve(params)


def fit_transit(photometry_csv, output_png, title="Transit Model Fit"):
    df = pd.read_csv(photometry_csv)

    if "time" in df.columns:
        jd = df["time"].to_numpy(dtype=float)
        jd0 = np.nanmin(jd)
        time_day = jd - jd0
        time_hours = time_day * 24.0

    elif "time_hours" in df.columns:
        time_hours = df["time_hours"].to_numpy(dtype=float)
        time_day = time_hours / 24.0

    elif "time_from_start_hours" in df.columns:
        time_hours = df["time_from_start_hours"].to_numpy(dtype=float)
        time_day = time_hours / 24.0

    else:
        raise ValueError("No valid time column found. Need 'time', 'time_hours', or 'time_from_start_hours'.")

    if "normalized_flux" in df.columns:
        flux = df["normalized_flux"].to_numpy(dtype=float)
    elif "relative_flux" in df.columns:
        flux = df["relative_flux"].to_numpy(dtype=float)
    elif "rel_flux" in df.columns:
        flux = df["rel_flux"].to_numpy(dtype=float)
    else:
        raise ValueError("No flux column found.")

    mask = np.isfinite(time_day) & np.isfinite(time_hours) & np.isfinite(flux)
    time_day = time_day[mask]
    time_hours = time_hours[mask]
    flux = flux[mask]

    idx = np.argsort(time_day)
    time_day = time_day[idx]
    time_hours = time_hours[idx]
    flux = flux[idx]

    flux = flux / np.nanmedian(flux)

    t0_guess = time_day[np.argmin(flux)]

    p0 = [t0_guess, 0.12, 3.0, 83.0]

    bounds = (
        [time_day.min(), 0.01, 1.0, 70.0],
        [time_day.max(), 0.30, 20.0, 90.0],
    )

    best_params, _ = curve_fit(
        transit_model,
        time_day,
        flux,
        p0=p0,
        bounds=bounds,
        maxfev=20000,
    )

    t0_fit, rp_fit, a_fit, inc_fit = best_params

    time_model_day = np.linspace(time_day.min(), time_day.max(), 1500)
    time_model_hours = time_model_day * 24.0
    model_flux = transit_model(time_model_day, t0_fit, rp_fit, a_fit, inc_fit)

    model_at_data = transit_model(time_day, t0_fit, rp_fit, a_fit, inc_fit)
    residual = flux - model_at_data
    rms = np.sqrt(np.mean(residual**2))

    plt.figure(figsize=(9, 5))
    plt.scatter(time_hours, flux, s=14, alpha=0.5, label="Observed data")
    plt.plot(time_model_hours, model_flux, linewidth=2, label="Transit model fit")
    plt.xlabel("Time from start (hours)")
    plt.ylabel("Normalized Flux")
    plt.title(title)
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_png, dpi=200)
    plt.close()

    return {
        "output_png": str(output_png),
        "t0_day_from_start": float(t0_fit),
        "t0_hour_from_start": float(t0_fit * 24.0),
        "rp_rs": float(rp_fit),
        "a_rs": float(a_fit),
        "inc": float(inc_fit),
        "rms": float(rms),
        "n_points": int(len(time_day)),
    }