import numpy as np
import batman
from scipy.optimize import curve_fit


def transit_model(t, t0, rp, a, inc):

    params = batman.TransitParams()

    params.t0 = t0
    params.per = 1.09142
    params.rp = rp
    params.a = a
    params.inc = inc

    params.ecc = 0.0
    params.w = 90.0

    params.u = [0.3, 0.2]
    params.limb_dark = "quadratic"

    m = batman.TransitModel(params, t)

    return m.light_curve(params)


def fit_transit(time, flux):

    flux = flux / np.nanmedian(flux)

    p0 = [
        time[np.argmin(flux)],
        0.12,
        3.0,
        83.0
    ]

    bounds = (
        [time.min(), 0.01, 1.0, 70.0],
        [time.max(), 0.30, 10.0, 90.0]
    )

    best_params, cov = curve_fit(
        transit_model,
        time,
        flux,
        p0=p0,
        bounds=bounds,
        maxfev=20000
    )

    t0_fit, rp_fit, a_fit, inc_fit = best_params

    model_flux = transit_model(
        time,
        t0_fit,
        rp_fit,
        a_fit,
        inc_fit
    )

    return {
        "t0": float(t0_fit),
        "rp_rs": float(rp_fit),
        "a_rs": float(a_fit),
        "inc": float(inc_fit),
        "model_flux": model_flux.tolist()
    }