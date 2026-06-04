from pathlib import Path
import numpy as np
import pandas as pd

from astropy.io import fits
from astropy.wcs import WCS
from astroquery.vizier import Vizier
import astropy.units as u
from astropy.coordinates import SkyCoord


def get_reference_fits_from_photometry(df):
    file_path = Path(df["file"].iloc[0])

    if not file_path.exists():
        raise FileNotFoundError(f"Reference FITS not found: {file_path}")

    return file_path


def pixel_to_radec(fits_file, x, y):
    header = fits.getheader(fits_file)
    wcs = WCS(header)

    if not wcs.has_celestial:
        raise ValueError(
            "This FITS file has no valid WCS. Plate solve first before catalog validation.")

    ra, dec = wcs.pixel_to_world_values(float(x), float(y))
    return float(ra), float(dec)


def query_gaia_catalog(ra, dec, radius_arcsec=3.0):
    Vizier.ROW_LIMIT = 5
    coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")

    result = Vizier.query_region(
        coord,
        radius=radius_arcsec * u.arcsec,
        catalog="I/355/gaiadr3",)

    if len(result) == 0:
        return None

    table = result[0]

    if len(table) == 0:
        return None

    row = table[0]

    return {
        "catalog": "Gaia DR3",
        "source_id": str(row["Source"]),
        "catalog_mag": float(row["Gmag"]),
        "catalog_mag_band": "G",}


def collect_measured_stars(df):
    stars = []

    # target
    if {"target_x", "target_y", "target_inst_mag"}.issubset(df.columns):
        stars.append({
            "star_name": "target",
            "x": float(pd.to_numeric(df["target_x"], errors="coerce").median()),
            "y": float(pd.to_numeric(df["target_y"], errors="coerce").median()),
            "inst_mag": float(pd.to_numeric(df["target_inst_mag"], errors="coerce").median()),
        })

    # comparison stars
    comp_indices = []

    for col in df.columns:
        if col.startswith("comp") and col.endswith("_x"):
            idx = col.replace("comp", "").replace("_x", "")
            comp_indices.append(idx)

    comp_indices = sorted(set(comp_indices), key=lambda v: int(v))

    for idx in comp_indices:
        x_col = f"comp{idx}_x"
        y_col = f"comp{idx}_y"
        mag_col = f"comp{idx}_inst_mag"

        if {x_col, y_col, mag_col}.issubset(df.columns):
            stars.append({
                "star_name": f"comp{idx}",
                "x": float(pd.to_numeric(df[x_col], errors="coerce").median()),
                "y": float(pd.to_numeric(df[y_col], errors="coerce").median()),
                "inst_mag": float(pd.to_numeric(df[mag_col], errors="coerce").median()),
            })

    return stars


def run_catalog_validation(
    photometry_csv,
    output_csv=None,
    radius_arcsec=3.0,
):
    photometry_csv = Path(photometry_csv)

    if output_csv is None:
        output_csv = photometry_csv.parent / "catalog_validation.csv"
    else:
        output_csv = Path(output_csv)

    df = pd.read_csv(photometry_csv)

    if len(df) == 0:
        raise ValueError("photometry CSV is empty")

    fits_file = get_reference_fits_from_photometry(df)
    measured_stars = collect_measured_stars(df)

    rows = []

    for star in measured_stars:
        ra, dec = pixel_to_radec(
            fits_file=fits_file,
            x=star["x"],
            y=star["y"])

        catalog = query_gaia_catalog(
            ra=ra,
            dec=dec,
            radius_arcsec=radius_arcsec)

        row = {
            **star,
            "ra_deg": ra,
            "dec_deg": dec}

        if catalog is None:
            row.update({
                "catalog": None,
                "source_id": None,
                "catalog_mag": np.nan,
                "catalog_mag_band": None,
                "individual_zeropoint": np.nan})
        else:
            individual_zp = catalog["catalog_mag"] - star["inst_mag"]

            row.update({
                **catalog,
                "individual_zeropoint": individual_zp})

        rows.append(row)

    result_df = pd.DataFrame(rows)

    comp_mask = result_df["star_name"].astype(str).str.startswith("comp")
    valid_comp = result_df[
        comp_mask
        & np.isfinite(result_df["individual_zeropoint"])]

    if len(valid_comp) == 0:
        raise ValueError("No valid comparison stars with catalog match found.")

    zeropoint_median = float(np.nanmedian(valid_comp["individual_zeropoint"]))
    zeropoint_std = float(np.nanstd(valid_comp["individual_zeropoint"]))

    result_df["zeropoint_median"] = zeropoint_median
    result_df["zeropoint_std"] = zeropoint_std

    result_df["calibrated_mag"] = (
        result_df["inst_mag"] + zeropoint_median)

    result_df["mag_error"] = (
        result_df["calibrated_mag"] - result_df["catalog_mag"])

    comp_errors = result_df.loc[comp_mask, "mag_error"]
    comp_errors = comp_errors[np.isfinite(comp_errors)]

    if len(comp_errors) > 0:
        comparison_rmse = float(np.sqrt(np.nanmean(comp_errors ** 2)))
        comparison_mae = float(np.nanmean(np.abs(comp_errors)))
    else:
        comparison_rmse = np.nan
        comparison_mae = np.nan

    result_df["comparison_rmse_mag"] = comparison_rmse
    result_df["comparison_mae_mag"] = comparison_mae

    result_df.to_csv(output_csv, index=False)

    return {
        "result_df": result_df,
        "zeropoint_median": zeropoint_median,
        "zeropoint_std": zeropoint_std,
        "comparison_rmse": comparison_rmse,
        "comparison_mae": comparison_mae,
        "output_csv": str(output_csv),
    }