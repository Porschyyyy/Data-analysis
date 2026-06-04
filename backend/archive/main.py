from pathlib import Path
import pandas as pd
from cosmic_ray import run_cosmic_ray_removal
from trim_utils import run_center_trim
from alignment import run_centroid_alignment
from photometry import run_aperture_photometry

from plot_lightcurve import (
    plot_lightcurve_both_styles,
    get_transit_info_from_data)

from fits_utils import (
    read_all_headers,
    summarize_header_values,
    show_values,
    add_standard_columns,
    summarize_standard_values,
    make_all_groups,
    print_groups,
    print_detected_frame_groups,
    ask_frame_role_map)

from calibration import (
    create_master_bias,
    create_master_dark,
    create_master_flat,
    calibrate_light_files,)


from backend.archive.gui_utils import (
    choose_folder,
    choose_reference_star_from_popup,
    select_multiple_star_positions_from_fits
)


def group_value_to_dict(group_value, group_keys):
    if group_value == "all" or len(group_keys) == 0:
        return {}

    if len(group_keys) == 1:
        return {group_keys[0]: group_value}

    return dict(zip(group_keys, group_value))


def find_matching_master_dark(light_meta, master_darks, dark_keys):
    light_exposure = light_meta.get("EXPOSURE_STD")

    for dark_group_value, dark_file in master_darks.items():
        dark_meta = group_value_to_dict(dark_group_value, dark_keys)

        if dark_meta.get("EXPOSURE_STD") == light_exposure:
            return dark_file

    return None


def find_matching_master_flat(light_meta, master_flats, flat_keys):
    light_filter = light_meta.get("FILTER_STD")

    for flat_group_value, flat_file in master_flats.items():
        flat_meta = group_value_to_dict(flat_group_value, flat_keys)

        if flat_meta.get("FILTER_STD") == light_filter:
            return flat_file

    return None


def main():
    raw_path = choose_folder("เลือกโฟลเดอร์ raw FITS")
    if raw_path is None:
        print("ไม่ได้เลือก raw folder")
        return

    output_path = choose_folder("เลือกโฟลเดอร์ output")
    if output_path is None:
        print("ไม่ได้เลือก output folder")
        return

    output_path.mkdir(exist_ok=True)

    print("Raw path:", raw_path)
    print("Output path:", output_path)

    fits_files = (
        list(raw_path.rglob("*.fits")) +
        list(raw_path.rglob("*.fit")) +
        list(raw_path.rglob("*.fts")))

    print("Raw path:", raw_path)
    print("Path exists:", raw_path.exists())
    print("Is directory:", raw_path.is_dir())
    print("\nจำนวนไฟล์ FITS ทั้งหมด:", len(fits_files))

    if len(fits_files) == 0:
        print("ไม่พบไฟล์ FITS")
        return

    df = read_all_headers(fits_files)

    df.to_csv(output_path / "fits_headers_raw.csv", index=False)

    header_summary = summarize_header_values(df)
    header_summary.to_csv(output_path / "header_summary.csv", index=False)

    print("\nสรุป header ที่มีค่าต่างกันมากที่สุด:")
    print(header_summary.head(30))

    print("\n========== Header สำคัญ ==========")
    show_values(df, [
        "folder",
        "IMAGETYP",
        "OBJECT",
        "FILTER",
        "EXPTIME",
        "EXPOSURE",
        "GAIN",
        "EGAIN",
        "CCD-TEMP",
        "SET-TEMP",
        "XBINNING",
        "YBINNING",
        "NAXIS1",
        "NAXIS2",
    ])


    df = add_standard_columns(df)

    print_detected_frame_groups(df)

    frame_role_map = ask_frame_role_map(df)

    df = add_standard_columns(
    df,
    frame_role_map=frame_role_map,)

    print("\n========== ค่ามาตรฐานสำหรับเตรียม group ==========")
    summarize_standard_values(df)

    df.to_csv(output_path / "fits_metadata_standard.csv", index=False)

    groups, used_keys = make_all_groups(df)

    print("\n========== Group keys ที่ใช้จริง ==========")
    print(used_keys)

    print("\n========== Groups สำหรับ calibration ==========")
    print_groups(groups, used_keys)

    master_path = output_path / "master"
    master_path.mkdir(exist_ok=True)

    overscan_slice = None
    trim_slice = None

    # -----------------------------
    # 1. Create Master Bias
    # -----------------------------
    master_bias = None

    bias_groups = groups["bias"]

    if len(bias_groups) > 0:
        first_bias_group = list(bias_groups.values())[0]

        master_bias = create_master_bias(
            bias_files=first_bias_group,
            output_file=master_path / "master_bias.fits",
            overscan_slice=overscan_slice,
            trim_slice=trim_slice,
            combine_method="median",
            skip_existing=False
        )
    else:
        print("ไม่พบ bias files สำหรับสร้าง master bias")

    # -----------------------------
    # 2. Create Master Dark
    # -----------------------------
    master_darks = {}

    for group_value, dark_files in groups["dark"].items():
        safe_name = (
            str(group_value)
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace(",", "_")
            .replace("'", "")
        )

        output_file = master_path / f"master_dark_{safe_name}.fits"

        master_dark = create_master_dark(
            dark_files=dark_files,
            output_file=output_file,
            master_bias=master_bias,
            overscan_slice=overscan_slice,
            trim_slice=trim_slice,
            combine_method="median",
            skip_existing=False
        )

        master_darks[group_value] = output_file

    # -----------------------------
    # 3. Create Master Flat
    # -----------------------------
    master_flats = {}

    for group_value, flat_files in groups["flat"].items():
        safe_name = (
            str(group_value)
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace(",", "_")
            .replace("'", "")
        )

        output_file = master_path / f"master_flat_{safe_name}.fits"

        master_flat = create_master_flat(
            flat_files=flat_files,
            output_file=output_file,
            master_bias=master_bias,
            master_dark=None,
            overscan_slice=overscan_slice,
            trim_slice=trim_slice,
            combine_method="median",
            skip_existing=False
        )

        master_flats[group_value] = output_file

    # -----------------------------
    # 4. Calibrate Light Frames
    # -----------------------------
    calibrated_path = output_path / "calibrated"
    calibrated_path.mkdir(exist_ok=True)

    master_bias_file = master_path / "master_bias.fits"

    for light_group_value, light_files in groups["light"].items():
        light_meta = group_value_to_dict(
            light_group_value,
            used_keys["light"]
        )

        matched_dark_file = find_matching_master_dark(
            light_meta,
            master_darks,
            used_keys["dark"]
        )

        matched_flat_file = find_matching_master_flat(
            light_meta,
            master_flats,
            used_keys["flat"]
        )

        print("\n========== CALIBRATING LIGHT GROUP ==========")
        print("Light group:", light_group_value)
        print("Light metadata:", light_meta)
        print("Matched dark:", matched_dark_file)
        print("Matched flat:", matched_flat_file)

        safe_group_name = (
            str(light_group_value)
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace(",", "_")
            .replace("'", "")
        )

        group_output_dir = calibrated_path / safe_group_name

        calibrate_light_files(
            light_files=light_files,
            output_dir=group_output_dir,
            master_bias_file=master_bias_file,
            master_dark_file=matched_dark_file,
            master_flat_file=matched_flat_file,
            overscan_slice=overscan_slice,
            trim_slice=trim_slice,
            skip_existing=False
        )


    # ==================================================
    # TRIM → COSMIC RAY REMOVAL → ALIGNMENT
    # ==================================================

    calibrated_path = output_path / "calibrated"
    trimmed_path = output_path / "trimmed"
    cosmic_path = output_path / "cosmic_cleaned"
    aligned_path = output_path / "aligned"

    # -----------------------------
    # 1. Trim calibrated images
    # -----------------------------

    print("\n========== TRIM SETTINGS ==========")
    print("เลือกวิธี trim ภาพ:")
    print("1 = ใช้ขนาดร่วมที่เล็กที่สุดของภาพทั้งหมดแบบอัตโนมัติ")
    print("2 = กรอก target_width และ target_height เอง")
    print("3 = ใช้ค่า default 4000 x 4000")
    
    trim_choice = input("เลือก 1/2/3 [1]: ").strip()
    
    if trim_choice == "":
        trim_choice = "1"
        
    if trim_choice == "1":
        run_center_trim(
            input_path=calibrated_path,
            output_path=trimmed_path,
            target_width=None,
            target_height=None,
            use_common_min_size=True,
            skip_existing=False,
            )
        
    elif trim_choice == "2":
        target_width = int(input("กรอก target_width เช่น 4000: ").strip())
        target_height = int(input("กรอก target_height เช่น 4000: ").strip())
        
        run_center_trim(
            input_path=calibrated_path,
            output_path=trimmed_path,
            target_width=target_width,
            target_height=target_height,
            use_common_min_size=False,
            skip_existing=False,
            )
        
    else:
        run_center_trim(
            input_path=calibrated_path,
            output_path=trimmed_path,
            target_width=4000,
            target_height=4000,
            use_common_min_size=False,
            skip_existing=False,
            )

    # -----------------------------
    # 2. Cosmic ray removal on trimmed images
    # -----------------------------
    
    run_cosmic_ray_removal(
        input_path=trimmed_path,
        output_path=cosmic_path,
        tile_size=512,
        sigclip=4.5,
        sigfrac=0.3,
        objlim=5.0,
        skip_existing=False
    )

    # -----------------------------
    # 3. Choose reference star from cosmic_cleaned
    # -----------------------------

    reference_file, x_star, y_star, box_size = choose_reference_star_from_popup(
        title="เลือก reference FITS จาก output/cosmic_cleaned",
        downsample=8,
        box_size=50,
        initial_dir=cosmic_path,
        )

    if reference_file is None:
        print("ไม่ได้เลือก reference file จึงข้าม alignment")
    else:

        # -----------------------------
        # 4. Alignment
        # -----------------------------

        run_centroid_alignment(
            input_path=cosmic_path,
            output_path=aligned_path,
            x_star=x_star,
            y_star=y_star,
            box_size=box_size,
            skip_existing=False
        )

        print("\nFinal files for photometry:")
        print(aligned_path)


    # ==================================================
    # PHOTOMETRY
    # ==================================================

    photometry_path = output_path / "photometry"
    photometry_path.mkdir(parents=True, exist_ok=True)

    photometry_csv = photometry_path / "photometry_results.csv"

    reference_file, _, _, _ = choose_reference_star_from_popup(
        title="เลือก reference FITS จาก output/aligned สำหรับ photometry",
        downsample=8,
        box_size=50,
        initial_dir=aligned_path,
        )

    if reference_file is None:
        print("ไม่ได้เลือก reference file จึงข้าม photometry")
    else:
        n_stars = int(input("ต้องการวัดดาวกี่ดวง? target + comparison stars: "))

        positions = select_multiple_star_positions_from_fits(
            reference_file,
            n_stars=n_stars,
            downsample=8,
        )

        df_phot = run_aperture_photometry(
            input_path=aligned_path,
            output_csv=photometry_csv,
            positions=positions,
            aperture_radius=None,
            annulus_inner=None,
            annulus_outer=None,
            centroid_box_size=None,
            recenter=True,
            auto_params=True,
            )

        print("\nPhotometry finished:")
        print(photometry_csv)


    # -----------------------------
    # PLOT LIGHT CURVE
    # -----------------------------

    # อ่านเวลาใน CSV เพื่อสรุปช่วงเวลา JD ของข้อมูล
    df_for_time = pd.read_csv(photometry_csv)
    df_for_time["time"] = pd.to_numeric(df_for_time["time"], errors="coerce")
    df_for_time = df_for_time.dropna(subset=["time"])

    mid_transit_jd, transit_duration_hours = get_transit_info_from_data(df_for_time)

    # สร้างกราฟทั้ง 2 แบบไว้เลย
    plot_result = plot_lightcurve_both_styles(
        photometry_csv=photometry_csv,
        output_dir=photometry_path,
        show=True,
        remove_first_point=False,
        remove_outliers=True,
        sigma_clip=None,
        bin_size=None,
        mid_transit_jd=mid_transit_jd,
        transit_duration_hours=transit_duration_hours,
        title="Light Curve",
    )

    print("\nLight curves saved:")
    print(plot_result)


    print("\nสร้าง master calibration files เรียบร้อย")
    print("Master files saved at:", master_path)

    print("\nบันทึกไฟล์แล้ว:")
    print(output_path / "fits_headers_raw.csv")
    print(output_path / "header_summary.csv")
    print(output_path / "fits_metadata_standard.csv")


if __name__ == "__main__":
    main()
