from PIL import Image

from ndstools.formats.graphics.palette import PaletteColor, RawPalette


def empty_im(
    im_size: tuple[int, int],
    colors: list[PaletteColor],
    bit_depth: int,
    transparency: bool,
):
    im = Image.new(mode="P", size=im_size)
    colors = [i for color in colors for i in color.to_int_list()]
    if len(colors) > 0x300:
        colors = colors[0:0x300]
    im.putpalette(colors)
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
    num_colors = 4
    match bit_depth:
        case 2:
            num_colors = 4
        case 4:
            num_colors = 16
        case 8:
            num_colors = 256
    pal = RawPalette(b"", try_decompress=False)
    step = 255 / (num_colors - 1)
    colors = []
    for i in range(num_colors):
        colors.append(PaletteColor.from_list([int(i * step)] * 3))
    if inverted:
        colors.reverse()
    pal.set_colors(colors)
    return pal
