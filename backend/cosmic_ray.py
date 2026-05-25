from pathlib import Path
from astropy.io import fits
import numpy as np
import astroscrappy


def get_fits_files(input_path):
    input_path = Path(input_path)

    return sorted(
        list(input_path.rglob("*.fits")) +
        list(input_path.rglob("*.fit")) +
        list(input_path.rglob("*.fts"))
    )


def remove_cosmic_ray_tile(
    tile_data,
    sigclip=4.5,
    sigfrac=0.3,
    objlim=5.0
):


    tile_data = np.asarray(tile_data, dtype=np.float32)

    mask, clean_tile = astroscrappy.detect_cosmics(
        tile_data,
        sigclip=sigclip,
        sigfrac=sigfrac,
        objlim=objlim,
        cleantype="medmask"
    )

    clean_tile = clean_tile.astype(np.float32)

    del mask

    return clean_tile


def remove_cosmic_ray_file_tiled(
    input_file,
    output_file,
    tile_size=512,
    sigclip=4.5,
    sigfrac=0.3,
    objlim=5.0,
    skip_existing=False
):

    input_file = Path(input_file)
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if skip_existing and output_file.exists():
        print(f"Skip cosmic existing: {output_file.name}")
        return

    print(f"Cosmic cleaning tiled: {input_file.name}")

    data, header = fits.getdata(input_file, header=True, memmap=True)
    data = np.asarray(data, dtype=np.float32)

    ny, nx = data.shape

    clean_data = np.empty_like(data, dtype=np.float32)

    for y0 in range(0, ny, tile_size):
        y1 = min(y0 + tile_size, ny)

        for x0 in range(0, nx, tile_size):
            x1 = min(x0 + tile_size, nx)

            tile = data[y0:y1, x0:x1]

            clean_tile = remove_cosmic_ray_tile(
                tile,
                sigclip=sigclip,
                sigfrac=sigfrac,
                objlim=objlim
            )

            clean_data[y0:y1, x0:x1] = clean_tile

            del tile
            del clean_tile

    header["HISTORY"] = "Cosmic ray removal by astroscrappy tiled"
    header["CRTILE"] = int(tile_size)
    header["CRSIGCL"] = float(sigclip)
    header["CRSIGFR"] = float(sigfrac)
    header["CROBJLM"] = float(objlim)
    header["BZERO"] = 0
    header["BSCALE"] = 1

    fits.writeto(
        output_file,
        clean_data,
        header=header,
        overwrite=True
    )

    del data
    del clean_data


def run_cosmic_ray_removal(
    input_path,
    output_path,
    tile_size=512,
    sigclip=4.5,
    sigfrac=0.3,
    objlim=5.0,
    skip_existing=False,
    progress_callback=None,
):

    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    fits_files = get_fits_files(input_path)

    print("\n========== COSMIC RAY REMOVAL ==========")
    print("Input :", input_path)
    print("Output:", output_path)
    print("Number of files:", len(fits_files))
    print("Tile size:", tile_size)

    if len(fits_files) == 0:
        print("No FITS files found for cosmic ray removal")
        return

    for i, input_file in enumerate(fits_files, start=1):
        relative_path = input_file.relative_to(input_path)
        output_file = output_path / relative_path

        print(f"\n[COSMIC {i}/{len(fits_files)}]")

        remove_cosmic_ray_file_tiled(
            input_file=input_file,
            output_file=output_file,
            tile_size=tile_size,
            sigclip=sigclip,
            sigfrac=sigfrac,
            objlim=objlim,
            skip_existing=skip_existing
        )

        if progress_callback is not None:
            progress_callback(
            i,
            len(fits_files),
            f"Removing cosmic rays: {Path(input_file).name}",
        )

    print("\nCosmic ray removal finished")