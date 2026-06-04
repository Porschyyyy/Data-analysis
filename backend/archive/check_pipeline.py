from pathlib import Path
import inspect
import pandas as pd


def check_function_signature(module_name, function_name, required_params):
    print(f"\n========== CHECK {module_name}.{function_name} ==========")

    try:
        module = __import__(module_name)
        func = getattr(module, function_name)
    except Exception as e:
        print("❌ Import failed:", e)
        return False

    sig = inspect.signature(func)
    params = list(sig.parameters.keys())

    print("Function signature:")
    print(sig)

    ok = True

    for p in required_params:
        if p in params:
            print(f"✅ has parameter: {p}")
        else:
            print(f"❌ missing parameter: {p}")
            ok = False

    return ok


def check_file_exists(path):
    path = Path(path)

    print(f"\n========== CHECK FILE ==========")
    print(path)

    if path.exists():
        print("✅ exists")
        return True

    print("❌ not found")
    return False


def check_photometry_csv(csv_path):
    csv_path = Path(csv_path)

    print("\n========== CHECK PHOTOMETRY CSV ==========")
    print(csv_path)

    if not csv_path.exists():
        print("❌ photometry_results.csv not found")
        return False

    df = pd.read_csv(csv_path)

    print("Rows:", len(df))
    print("Columns:")
    print(list(df.columns))

    required_cols = [
        "time",
        "target_flux",
        "comparison_flux_sum",
        "relative_flux",
        "normalized_flux",
    ]

    ok = True

    for col in required_cols:
        if col in df.columns:
            print(f"✅ has column: {col}")
        else:
            print(f"❌ missing column: {col}")
            ok = False

    if "time" in df.columns:
        df["time"] = pd.to_numeric(df["time"], errors="coerce")
        start_jd = df["time"].min()
        end_jd = df["time"].max()
        duration_hours = (end_jd - start_jd) * 24

        print(f"\nStart JD      : {start_jd}")
        print(f"End JD        : {end_jd}")
        print(f"Duration hours: {duration_hours:.3f}")

    if "normalized_flux" in df.columns:
        df["normalized_flux"] = pd.to_numeric(df["normalized_flux"], errors="coerce")
        print("\nNormalized flux:")
        print("min :", df["normalized_flux"].min())
        print("max :", df["normalized_flux"].max())
        print("std :", df["normalized_flux"].std())

    # เช็กว่า recenter ทำงานจริงไหม
    position_cols = [
        col for col in df.columns
        if col.endswith("_x") or col.endswith("_y")
    ]

    if position_cols:
        print("\nPosition column movement check:")
        for col in position_cols:
            try:
                values = pd.to_numeric(df[col], errors="coerce")
                movement = values.max() - values.min()
                print(f"{col}: movement = {movement:.4f}")
            except Exception:
                pass

    return ok


def main():
    base_dir = Path(__file__).resolve().parent
    project_dir = base_dir.parent

    photometry_csv = project_dir / "output" / "photometry" / "photometry_results.csv"

    all_ok = True

    # main.py ตอนนี้เรียก photometry ด้วยพารามิเตอร์เหล่านี้
    all_ok &= check_function_signature(
        module_name="photometry",
        function_name="run_aperture_photometry",
        required_params=[
            "input_path",
            "output_csv",
            "positions",
            "aperture_radius",
            "annulus_inner",
            "annulus_outer",
            "centroid_box_size",
            "recenter",
            "auto_params",
        ],
    )

    # plot_lightcurve.py เวอร์ชันใหม่ควรรองรับพารามิเตอร์เหล่านี้
    all_ok &= check_function_signature(
        module_name="plot_lightcurve",
        function_name="plot_lightcurve",
        required_params=[
            "photometry_csv",
            "output_png",
            "show",
            "remove_first_point",
            "remove_outliers",
            "sigma_clip",
            "bin_size",
            "mid_transit_jd",
            "transit_duration_hours",
            "plot_style",
        ],
    )

    check_file_exists(photometry_csv)
    check_photometry_csv(photometry_csv)

    print("\n========== SUMMARY ==========")

    if all_ok:
        print("✅ Pipeline function signatures look OK.")
    else:
        print("❌ Some function signatures are not compatible.")
        print("ให้แก้ไฟล์ที่ขึ้น missing parameter ก่อนรัน main.py ใหม่")


if __name__ == "__main__":
    main()