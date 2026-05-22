from astropy.io import fits
import pandas as pd
import numpy as np


GROUP_CANDIDATES = {
    "light": [
        "OBJECT",
        "FILTER_STD",
        "EXPOSURE_STD",
        "GAIN_STD",
        "BINNING_STD",
        "IMAGE_SIZE",
    ],

    "dark": [
        "EXPOSURE_STD",
        "GAIN_STD",
        "TEMP_STD",
        "BINNING_STD",
        "IMAGE_SIZE",
    ],

    "flat": [
        "FILTER_STD",
        "EXPOSURE_STD",
        "GAIN_STD",
        "BINNING_STD",
        "IMAGE_SIZE",
    ],

    "bias": [
        "GAIN_STD",
        "BINNING_STD",
        "IMAGE_SIZE",
    ],
}


def clean_header_value(value):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


def read_all_headers(fits_files):
    rows = []

    for f in fits_files:
        try:
            hdr = fits.getheader(f)

            row = {
                "file": str(f),
                "filename": f.name,
                "folder": f.parent.name,
            }

            for key in hdr.keys():
                if key in ["COMMENT", "HISTORY"]:
                    continue

                row[key] = clean_header_value(hdr.get(key))

            rows.append(row)

        except Exception as e:
            rows.append({
                "file": str(f),
                "filename": f.name,
                "folder": f.parent.name,
                "error": str(e),
            })

    return pd.DataFrame(rows)


def summarize_header_values(df):
    summary = []
    ignore_cols = ["file", "filename", "error"]

    for col in df.columns:
        if col in ignore_cols:
            continue

        values = df[col].dropna()
        safe_values = values.astype(str)
        unique_values = safe_values.unique()

        summary.append({
            "HEADER": col,
            "NON_NULL_COUNT": len(values),
            "UNIQUE_COUNT": len(unique_values),
            "EXAMPLE_VALUES": list(unique_values[:10]),
        })

    summary_df = pd.DataFrame(summary)

    summary_df = summary_df.sort_values(
        by=["UNIQUE_COUNT", "NON_NULL_COUNT"],
        ascending=[False, False],
    )

    return summary_df


def show_values(df, columns):
    for col in columns:
        if col in df.columns:
            print(f"\n===== {col} =====")
            print("จำนวนค่าที่แตกต่าง:", df[col].dropna().nunique())
            print(df[col].dropna().value_counts())
        else:
            print(f"\nไม่พบ header: {col}")


FRAME_GROUP_HEADER_CANDIDATES = [
    "IMAGETYP",
    "IMAGETYPE",
    "FRAME",
    "FRAMETYP",
    "FRAME_TYPE",
    "OBSTYPE",
    "OBJECT",
]


def find_frame_group_column(df):
    for col in FRAME_GROUP_HEADER_CANDIDATES:
        if col in df.columns:
            values = df[col].dropna().astype(str).str.strip()
            values = values[values != ""]

            if len(values) > 0:
                return col

    return None


def add_raw_frame_group(df, frame_group_column=None):
    df = df.copy()

    if frame_group_column is None:
        frame_group_column = find_frame_group_column(df)

    if frame_group_column is None:
        df["RAW_FRAME_GROUP"] = df["folder"].astype(str)
        df["FRAME_GROUP_SOURCE"] = "folder"
    else:
        df["RAW_FRAME_GROUP"] = df[frame_group_column].astype(str).str.strip()
        df["FRAME_GROUP_SOURCE"] = frame_group_column

    return df


def print_detected_frame_groups(df, max_files=3):
    print("\n========== DETECTED FRAME GROUPS ==========")

    if "RAW_FRAME_GROUP" not in df.columns:
        df = add_raw_frame_group(df)

    for i, (group_name, group_df) in enumerate(
        df.groupby("RAW_FRAME_GROUP", dropna=False),
        start=1,
    ):
        print(f"\n[{i}] Group: {group_name}")
        print("จำนวนไฟล์:", len(group_df))

        print("\nตัวอย่างไฟล์:")
        for filename in group_df["filename"].head(max_files):
            print("-", filename)

        print("\nHeader summary:")

        for col in [
            "IMAGETYP",
            "OBJECT",
            "EXPTIME",
            "EXPOSURE",
            "FILTER",
            "CCD-TEMP",
            "SET-TEMP",
            "XBINNING",
            "YBINNING",
            "NAXIS1",
            "NAXIS2",
        ]:
            if col in group_df.columns:
                values = group_df[col].dropna().unique()

                if len(values) > 0:
                    shown_values = list(values[:10])
                    print(f"{col}: {shown_values}")

        print("-----------------------------------")


def ask_frame_role_map(df):
    role_map = {}

    if "RAW_FRAME_GROUP" not in df.columns:
        df = add_raw_frame_group(df)

    group_names = list(df["RAW_FRAME_GROUP"].dropna().unique())

    print("\n========== SET FRAME ROLES ==========")
    print("เลือก role ให้แต่ละ group: bias / dark / flat / light / skip")

    for group_name in group_names:
        while True:
            role = input(
                f'\nGroup "{group_name}" ตั้งเป็นอะไร? '
                "(bias/dark/flat/light/skip): "
            ).strip().lower()

            if role in ["bias", "dark", "flat", "light", "skip"]:
                role_map[group_name] = role
                break

            print("กรุณาพิมพ์เฉพาะ bias, dark, flat, light หรือ skip")

    print("\n========== ROLE MAP ==========")
    for group_name, role in role_map.items():
        print(f"{group_name} -> {role}")

    return role_map


def classify_frame_type_from_folder(folder_name):
    folder = str(folder_name).lower()

    if "bias" in folder:
        return "bias"

    if "dark" in folder:
        return "dark"

    if "flat" in folder:
        return "flat"

    if "object" in folder or "light" in folder:
        return "light"

    return "unknown"


def get_first_existing_value(row, possible_keys):
    for key in possible_keys:
        if key in row.index:
            value = row[key]

            if pd.notna(value):
                return value

    return np.nan


def add_standard_columns(df, frame_role_map=None, frame_group_column=None):
    df = df.copy()

    df = add_raw_frame_group(
        df,
        frame_group_column=frame_group_column,
    )

    if frame_role_map is None:
        df["FRAME_TYPE"] = "unassigned"
    else:
        df["FRAME_TYPE"] = df["RAW_FRAME_GROUP"].map(frame_role_map)
        df["FRAME_TYPE"] = df["FRAME_TYPE"].fillna("unassigned")

    df["EXPOSURE_STD"] = df.apply(
        lambda row: get_first_existing_value(row, ["EXPTIME", "EXPOSURE"]),
        axis=1,
    )

    df["FILTER_STD"] = df.apply(
        lambda row: get_first_existing_value(row, ["FILTER", "FILTER1"]),
        axis=1,
    )

    df["GAIN_STD"] = df.apply(
        lambda row: get_first_existing_value(row, ["GAIN", "EGAIN"]),
        axis=1,
    )

    df["TEMP_STD"] = df.apply(
        lambda row: get_first_existing_value(
            row,
            ["CCD-TEMP", "CCD_TEMP", "SET-TEMP", "TEMP"],
        ),
        axis=1,
    )

    df["EXPOSURE_STD"] = pd.to_numeric(
        df["EXPOSURE_STD"],
        errors="coerce",
    ).round(2)

    df["TEMP_STD"] = pd.to_numeric(
        df["TEMP_STD"],
        errors="coerce",
    ).round(1)

    if "XBINNING" in df.columns and "YBINNING" in df.columns:
        df["BINNING_STD"] = (
            df["XBINNING"].astype(str) + "x" + df["YBINNING"].astype(str)
        )
    elif "BINNING" in df.columns:
        df["BINNING_STD"] = df["BINNING"]
    else:
        df["BINNING_STD"] = np.nan

    if "NAXIS1" in df.columns and "NAXIS2" in df.columns:
        df["IMAGE_SIZE"] = (
            df["NAXIS1"].astype(str) + "x" + df["NAXIS2"].astype(str)
        )
    else:
        df["IMAGE_SIZE"] = np.nan

    return df


def summarize_standard_values(df):
    columns = [
        "FRAME_TYPE",
        "EXPOSURE_STD",
        "FILTER_STD",
        "GAIN_STD",
        "TEMP_STD",
        "BINNING_STD",
        "IMAGE_SIZE",
        "OBJECT",
    ]

    for col in columns:
        if col in df.columns:
            print(f"\n===== {col} =====")
            print("จำนวนค่าที่แตกต่าง:", df[col].dropna().nunique())
            print(df[col].dropna().value_counts())


def choose_group_keys(df, candidate_keys):
    selected_keys = []

    for key in candidate_keys:
        if key not in df.columns:
            continue

        values = df[key].dropna()

        if len(values) == 0:
            continue

        if values.nunique() > 1:
            selected_keys.append(key)

    return selected_keys


def group_files_for_calibration(df, frame_type):
    sub_df = df[df["FRAME_TYPE"] == frame_type].copy()

    if len(sub_df) == 0:
        return {}, []

    candidate_keys = GROUP_CANDIDATES[frame_type]
    group_keys = choose_group_keys(sub_df, candidate_keys)

    if len(group_keys) == 0:
        return {"all": sub_df["file"].tolist()}, []

    groups = {}

    for group_value, group_df in sub_df.groupby(group_keys, dropna=False):
        groups[group_value] = group_df["file"].tolist()

    return groups, group_keys


def make_all_groups(df):
    groups = {}
    used_keys = {}

    for frame_type in ["light", "dark", "flat", "bias"]:
        group_dict, group_keys = group_files_for_calibration(df, frame_type)

        groups[frame_type] = group_dict
        used_keys[frame_type] = group_keys

    return groups, used_keys


def print_groups(groups, used_keys):
    for frame_type, group_dict in groups.items():
        print(f"\n===== {frame_type.upper()} =====")
        print("ใช้ keys:", used_keys[frame_type])
        print("จำนวน groups:", len(group_dict))

        if len(group_dict) == 0:
            print("ไม่พบไฟล์")
            continue

        for group_value, files in group_dict.items():
            print("\nGroup:", group_value)
            print("จำนวนไฟล์:", len(files))
            print("ตัวอย่าง:", files[:2])