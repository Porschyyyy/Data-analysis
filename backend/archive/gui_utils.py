from pathlib import Path
from tkinter import Tk, filedialog

from astropy.io import fits
import numpy as np
import matplotlib.pyplot as plt


def choose_folder(title="Choose folder"):
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    folder = filedialog.askdirectory(title=title)

    root.destroy()

    if folder == "":
        return None

    return Path(folder)


def choose_fits_file(title="Choose FITS file", initial_dir=None):
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    ask_kwargs = {
        "title": title,
        "filetypes": [
            ("FITS files", "*.fits *.fit *.fts"),
            ("All files", "*.*"),
        ],
    }

    if initial_dir is not None:
        initial_dir = Path(initial_dir)
        if initial_dir.exists():
            ask_kwargs["initialdir"] = str(initial_dir)

    file_path = filedialog.askopenfilename(**ask_kwargs)

    root.destroy()

    if file_path == "":
        return None

    return Path(file_path)


def select_star_position_from_fits(
    fits_file,
    downsample=8,
    percentile_low=1,
    percentile_high=99.5,
):
    
    fits_file = Path(fits_file)

    print("\nLoading reference image:")
    print(fits_file)

    data = fits.getdata(fits_file, memmap=True)
    data = np.asarray(data, dtype=np.float32)

    print("Original image shape:", data.shape)

    # สร้างภาพย่อสำหรับแสดง
    display_data = data[::downsample, ::downsample]

    vmin = np.nanpercentile(display_data, percentile_low)
    vmax = np.nanpercentile(display_data, percentile_high)

    fig, ax = plt.subplots(figsize=(10, 10))

    ax.imshow(
        display_data,
        origin="lower",
        cmap="gray",
        vmin=vmin,
        vmax=vmax,
    )

    ax.set_title(
        "Click reference star 1 time, then close window\n"
        f"Displayed image is downsampled by {downsample}x"
    )

    ax.set_xlabel("X display pixel")
    ax.set_ylabel("Y display pixel")

    print("\nคลิกดาวอ้างอิง 1 ครั้งในหน้าต่างรูป")
    print("หลังคลิกแล้วปิดหน้าต่างรูปได้เลย")

    clicked = plt.ginput(1, timeout=0)

    plt.close(fig)

    if len(clicked) == 0:
        raise RuntimeError("ไม่ได้คลิกเลือกดาว")

    x_display, y_display = clicked[0]

    x_star = x_display * downsample
    y_star = y_display * downsample

    print("\nSelected reference star position:")
    print("x_star =", x_star)
    print("y_star =", y_star)

    del data
    del display_data

    return float(x_star), float(y_star)


def choose_reference_star_from_popup(
    title="เลือก reference FITS สำหรับ alignment",
    downsample=8,
    box_size=50,
    initial_dir=None,
):

    reference_file = choose_fits_file(
        title=title,
        initial_dir=initial_dir,
    )

    if reference_file is None:
        print("ไม่ได้เลือก reference file")
        return None, None, None, None

    x_star, y_star = select_star_position_from_fits(
        reference_file,
        downsample=downsample,
    )

    return reference_file, x_star, y_star, box_size


def select_multiple_star_positions_from_fits(
    fits_file,
    n_stars,
    downsample=8,
    percentile_low=1,
    percentile_high=99.5,
):

    fits_file = Path(fits_file)

    print("\nLoading reference image:")
    print(fits_file)

    data = fits.getdata(fits_file, memmap=True)
    data = np.asarray(data, dtype=np.float32)

    print("Original image shape:", data.shape)

    display_data = data[::downsample, ::downsample]

    vmin = np.nanpercentile(display_data, percentile_low)
    vmax = np.nanpercentile(display_data, percentile_high)

    fig, ax = plt.subplots(figsize=(10, 10))

    ax.imshow(
        display_data,
        origin="lower",
        cmap="gray",
        vmin=vmin,
        vmax=vmax,
    )

    ax.set_title(
        f"Click {n_stars} stars: target first, then comparison stars\n"
        f"Displayed image is downsampled by {downsample}x"
    )

    ax.set_xlabel("X display pixel")
    ax.set_ylabel("Y display pixel")

    print(f"\nคลิกดาวทั้งหมด {n_stars} ดวง")
    print("ลำดับ: target ก่อน แล้วตามด้วย comparison stars")

    clicked = plt.ginput(n_stars, timeout=0)

    plt.close(fig)

    if len(clicked) != n_stars:
        raise RuntimeError(f"เลือกดาวได้ {len(clicked)} ดวง แต่ต้องการ {n_stars} ดวง")

    positions = []

    for x_display, y_display in clicked:
        x_real = x_display * downsample
        y_real = y_display * downsample
        positions.append((float(x_real), float(y_real)))

    print("\nSelected star positions:")
    for i, (x, y) in enumerate(positions):
        if i == 0:
            print(f"Target     : x={x:.2f}, y={y:.2f}")
        else:
            print(f"Comparison {i}: x={x:.2f}, y={y:.2f}")

    del data
    del display_data

    return positions