import struct
from PIL import Image

from src.ndstools.fs import EndianBinaryStreamReader
from src.ndstools.formats.graphics.Palette import PaletteColor, RawPalette
from typing import Tuple, List


def eightbpp_to_fourbpp(data: bytes | bytearray):
    newdata = bytearray()
    it = iter(data)
    for _ in range(len(data) // 2):
        val1 = next(it) % 0x10
        val2 = next(it) % 0x10
        newdata += struct.pack("<B", val2 * 0x10 + val1)
    return newdata


def fourbpp_to_eightbpp(data: bytes | bytearray, pal_idx: int = 0):
    newdata = bytearray()
    for val in data:
        p1 = (val % 0x10) + (0x10 * pal_idx)
        p2 = (val // 0x10) + (0x10 * pal_idx)
        newdata += struct.pack("<B", p1) + struct.pack("<B", p2)
    return newdata


def twobpp_to_eightbpp(data: bytes | bytearray, pal_idx: int = 0):
    newdata = bytearray()
    for val in data:
        p1 = (val & 0x3) + (0x4 * pal_idx)
        p2 = ((val >> 2) & 0x3) + (0x4 * pal_idx)
        p3 = ((val >> 4) & 0x3) + (0x4 * pal_idx)
        p4 = ((val >> 6) & 0x3) + (0x4 * pal_idx)
        newdata += (
            struct.pack("<B", p4)
            + struct.pack("<B", p3)
            + struct.pack("<B", p2)
            + struct.pack("<B", p1)
        )
    return newdata


def eightbpp_to_twobpp(data: bytes | bytearray):
    newdata = bytearray()
    it = iter(data)
    for _ in range(len(data) // 4):
        val1 = next(it) % 0x4
        val2 = next(it) % 0x4
        val3 = next(it) % 0x4
        val4 = next(it) % 0x4
        newdata += struct.pack("<B", (val4 << 6) + (val3 << 4) + (val2 << 2) + val1)
    return newdata


def convert_from_eightbpp(data: bytes | bytearray, bit_depth: int):
    """
    Convert an 8 bytes per pixel data stream to an N bytes per pixel data stream, with N in [2, 4, 8].

    :params data: A bytes stream.
    :params bit_depth: The bit depth the new stream should have.

    :returns: A new stream with the given bit depth.
    """
    assert bit_depth in [2, 4, 8]
    if bit_depth == 2:
        return eightbpp_to_twobpp(data)
    elif bit_depth == 4:
        return eightbpp_to_fourbpp(data)
    else:
        return data


def convert_to_eightbpp(data: bytes | bytearray, bit_depth: int, pal_idx: int = 0):
    """
    Convert an N bytes per pixel data stream to an 8 bytes per pixel data stream, with N in [2, 4, 8].

    :params data: A bytes stream.
    :params bit_depth: The bit depth the new stream should have.
    :params pal_idx: The palette idx the pixels should be pushed to. For example, if you convert a 4bpp stream to 8bpp with pal_idx = 1, the pixels with be written with values between 0x10 and 0x20.
    :returns: A new stream with a bit depth of 8.
    """
    assert bit_depth in [2, 4, 8]
    if bit_depth == 2:
        return twobpp_to_eightbpp(data, pal_idx)
    elif bit_depth == 4:
        return fourbpp_to_eightbpp(data, pal_idx)
    else:
        return data


def empty_im(
    im_size: tuple[int, int],
    colors: list[PaletteColor],
    bit_depth: int,
    transparency: bool,
):
    im = Image.new(mode="P", size=im_size)

    im.putpalette([i for color in colors for i in color.to_int_list()])
    if transparency:
        if bit_depth == 2:
            im.info["transparency"] = (b"\x00" + b"\xff" * 3) * 64
        if bit_depth == 4:
            im.info["transparency"] = (b"\x00" + b"\xff" * 15) * 16
        elif bit_depth == 8:
            im.info["transparency"] = 0
    # im.apply_transparency()
    return im


def get_image_colors(im: Image.Image):
    pal = im.getpalette(rawmode="RGB")
    if not pal:
        raise Exception("No palette found on image")
    colors = [
        PaletteColor.from_list(pal[3 * i : 3 * (i + 1)]) for i in range(len(pal) // 3)
    ]
    return colors


def sum_colors(colors1: list[int], colors2: list[int], w1: int, w2: int):
    return [
        (colors1[0] * w1 + colors2[0] * w2) // (w1 + w2),  # R
        (colors1[1] * w1 + colors2[1] * w2) // (w1 + w2),  # G
        (colors1[2] * w1 + colors2[2] * w2) // (w1 + w2),  # B
    ]


def paste_alpha(
    src_im: Image.Image,
    pasted_im: Image.Image,
    region: tuple[int, int],
    transparency_idx: list[int],
):
    src_region = src_im.crop(
        (
            region[0],
            region[1],
            region[0] + pasted_im.width,
            region[1] + pasted_im.height,
        )
    )
    assert src_region.size == pasted_im.size
    src_region_data = list(src_region.getdata())
    pasted_im_data = list(pasted_im.getdata())
    for idx, _ in enumerate(src_region_data):
        newpix = pasted_im_data[idx]
        if newpix not in transparency_idx:
            src_region_data[idx] = newpix
    src_region.putdata(src_region_data)
    src_im.paste(src_region, region)
    return src_im

def new_bw_palette(bit_depth: int, inverted: bool = False):
    num_colors = None
    match bit_depth:
        case 2:
            num_colors = 4
        case 4:
            num_colors = 16
        case 8:
            num_colors = 256
    pal = RawPalette(b'')
    step = 255 / (num_colors  - 1)
    colors = []
    for i in range(num_colors):
        colors.append(PaletteColor.from_list([int(i * step)] * 3))
    if inverted:
        colors.reverse()
    pal.set_colors(colors)
    return pal

def texel_decompress(
    data: bytes, info: bytes, colors: list[PaletteColor], im_size: tuple[int, int]
) -> Tuple[bytes, List[int]]:
    # TODO: remove palette stuff in this and move the function in the models folder

    def get_rgb(pal_index: int):
        return colors[pal_index].to_int_list()

    width, height = im_size
    finf = EndianBinaryStreamReader(info)
    fdat = EndianBinaryStreamReader(data)
    out_data = bytearray(width * height)
    # force first index to be the transparent
    new_colors = [[-1, -1, -1]]
    for j in range(0, height, 4):
        for i in range(0, width, 4):
            tex_data = fdat.read_UInt32()
            pal_info = finf.read_UInt16()
            pal_offset = pal_info & 0x3FFF
            pal_idx_start = pal_offset * 2
            pal_mode = pal_info >> 14
            for hTex in range(4):
                texel_row = (tex_data >> (hTex * 8)) & 0xFF
                for wTex in range(4):
                    texel = (texel_row >> (wTex * 2)) & 0x3
                    pal_index = pal_idx_start + texel
                    match pal_mode:
                        case 0:
                            if texel == 3:
                                pix_colors = [-1, -1, -1]  # transparent
                            else:
                                pix_colors = get_rgb(pal_index)

                        case 1:
                            if texel == 0:
                                pix_colors = get_rgb(pal_index)
                            elif texel == 1:
                                pix_colors = get_rgb(pal_index)
                            elif texel == 2:
                                pix_colors = sum_colors(
                                    get_rgb(pal_idx_start),
                                    get_rgb(pal_idx_start + 1),
                                    1,
                                    1,
                                )
                            elif texel == 3:
                                pix_colors = [-1, -1, -1]  # transparent

                        case 2:
                            pix_colors = get_rgb(pal_index)

                        case 3:
                            if texel == 0:
                                pix_colors = get_rgb(pal_index)
                            elif texel == 1:
                                pix_colors = get_rgb(pal_index)
                            elif texel == 2:
                                pix_colors = sum_colors(
                                    get_rgb(pal_idx_start),
                                    get_rgb(pal_idx_start + 1),
                                    5,
                                    3,
                                )
                            elif texel == 3:
                                pix_colors = sum_colors(
                                    get_rgb(pal_idx_start),
                                    get_rgb(pal_idx_start + 1),
                                    3,
                                    5,
                                )

                    try:
                        val = new_colors.index(pix_colors)
                    except ValueError:
                        val = len(new_colors)
                        new_colors.append(pix_colors)
                    out_data[(hTex + j) * width + wTex + i] = val
    new_colors[0] = [0, 0, 0]
    out_colors = []
    for colors in new_colors:
        out_colors.extend(colors)
    return out_data, out_colors
