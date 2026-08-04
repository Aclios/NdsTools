from ndstools.formats.graphics import ImageCanva
from ndstools.fs import EndianBinaryReader, EndianBinaryStreamReader
from ndstools.formats.graphics import RawBitmap, RawPalette, PaletteColor

from pathlib import Path
from typing import List, Tuple
from enum import IntEnum


class TexFormat(IntEnum):
    A3I5 = 1
    I2 = 2
    I4 = 3
    I8 = 4
    TexelCompressed = 5
    A5I3 = 6
    A1BGR555 = 7

    @property
    def bit_depth(self):
        match self.name:
            case "A3I5" | "I8" | "TexelCompressed" | "A5I3":
                return 8
            case "I4":
                return 4
            case "I2":
                return 2
            case "A1BGR555":
                return 16

    @property
    def palette_size(self):
        match self.name:
            case "A1BGR555":
                return 0
            case "I2":
                return 8
            case "A5I3":
                return 0x10
            case "I4":
                return 0x20
            case "A3I5":
                return 0x40
            case "TexelCompressed" | "I8":
                return 0x200

    def build_image(
        self,
        im_size: tuple[int, int],
        bitmap_data: bytes,
        palette_data: bytes,
        compression_info_data: bytes,
    ):
        transparency = False
        match self.name:
            case "TexelCompressed":
                transparency = True
                palette = RawPalette(palette_data)
                data, new_colors = texel_decompress(
                    bitmap_data,
                    compression_info_data,
                    palette.get_colors(),
                    im_size,
                )
                bitmap = RawBitmap(data)
                palette.set_colors(new_colors)

            case "I2" | "I4" | "I8":
                bitmap = RawBitmap(bitmap_data)
                palette = RawPalette(palette_data)

            case _:
                raise Exception(f"Unsupported texture mode: {self.name}")

        im = ImageCanva(
            bitmap=bitmap,
            palette=palette,
            bit_depth=self.bit_depth,
            im_size=im_size,
            linear=True,
            transparency=transparency,
        )
        im.resolve()
        return im.image


class TEX0:
    def __repr__(self):
        out = f"Number of textures: {self.tex_info.tex_count}\n"
        for idx, tex in enumerate(self.tex_info.parameters):
            pal = self.pal_info.parameters[idx]
            out += f"Name: {self.tex_info.names[idx]}, format: {tex.format.name}, bitmap_offset: {hex(self.offset + self.tex_data_offset + tex.tex_offset * 8)}, pal_offset: {hex(self.offset + self.palette_data_offset + pal.pal_offset * 0x8)} \n"
        return out

    def __init__(self, f: EndianBinaryReader):
        self.offset = f.tell()
        self.magic = f.check_magic(b"TEX0")
        self.section_size = f.read_UInt32()

        self.padding1 = f.read_UInt32()
        self.tex_region_size = f.read_UInt16()
        self.tex_info_offset = f.read_UInt16()
        self.padding2 = f.read_UInt32()
        self.tex_data_offset = f.read_UInt32()
        self.padding3 = f.read_UInt32()
        self.tex_compressed_region_size = f.read_UInt16() << 3
        self.tex_compressed_info_offset = f.read_UInt16()
        self.padding4 = f.read_UInt32()
        self.tex_compressed_data_offset = f.read_UInt32()
        self.tex_compressed_info_data_offset = f.read_UInt32()
        self.padding5 = f.read_UInt32()
        self.palette_data_size = f.read_UInt32() << 3
        self.palette_info_offset = f.read_UInt32()
        self.palette_data_offset = f.read_UInt32()

        f.seek(self.offset + self.tex_info_offset)
        self.tex_info = TexInfo(f)

        f.seek(self.offset + self.palette_info_offset)
        self.pal_info = PaletteInfo(f)

        self.calculate_compression_info_offsets()

        f.seek(self.offset)
        self.raw_data = f.read(self.section_size)

    def export_textures(self, out_dir: str):
        Path(out_dir).mkdir(exist_ok=True, parents=True)
        for tex_idx, param in enumerate(self.tex_info.parameters):
            pal_idx = self.get_related_palette_idx(param.name, tex_idx)
            bitmap, palette, comp_info = self.get_texture_data(tex_idx, pal_idx)
            im = param.format.build_image(
                (param.width, param.height), bitmap, palette, comp_info
            )
            im.save(Path(out_dir) / f"{param.name}.png")

    def get_texture_data(self, tex_idx: int, palette_idx: int):
        if tex_idx >= len(self.tex_info.parameters):
            raise Exception(
                f"Given idx ({tex_idx}) is beyond max tex idx ({len(self.tex_info.parameters)})"
            )
        parameters = self.tex_info.parameters[tex_idx]

        if parameters.format.name == "TexelCompressed":
            bitmap_offset = (
                self.tex_compressed_data_offset + parameters.tex_offset * 0x8
            )
            bitmap_size = parameters.width * parameters.height // 4
        else:
            bitmap_offset = self.tex_data_offset + parameters.tex_offset * 8
            bitmap_size = (
                parameters.width * parameters.height * parameters.format.bit_depth // 8
            )
        bitmap_data = self.raw_data[bitmap_offset : bitmap_offset + bitmap_size]

        palette_offset = (
            self.palette_data_offset
            + self.pal_info.parameters[palette_idx].pal_offset * 0x8
        )
        if parameters.format.name == "TexelCompressed":
            palette_data = self.raw_data[palette_offset:]

        else:
            palette_size = parameters.format.palette_size
            palette_data = self.raw_data[palette_offset : palette_offset + palette_size]

        if parameters.format.name == "TexelCompressed":
            compression_info_offset = (
                self.tex_compressed_info_data_offset
                + parameters.compression_info_offset
            )
            compression_info_size = parameters.width * parameters.height // 8
            info_data = self.raw_data[
                compression_info_offset : compression_info_offset
                + compression_info_size
            ]
        else:
            info_data = bytes()

        return bitmap_data, palette_data, info_data

    def calculate_compression_info_offsets(self):
        compression_info_offset = 0
        for parameters in self.tex_info.parameters:
            if parameters.format.name == "TexelCompressed":
                parameters.compression_info_offset = compression_info_offset
                compression_info_offset += (parameters.width * parameters.height) // 8

    def get_related_palette_idx(self, tex_name: str, tex_idx: int):
        pal_name = (tex_name + "_pl")[:0x10]
        try:
            pal_idx = self.pal_info.name_map[pal_name]
        except KeyError:
            pal_idx = tex_idx
        return pal_idx


class TexInfo:
    def __init__(self, f: EndianBinaryReader):
        self.unk = f.read_UInt8()
        self.tex_count = f.read_UInt8()
        self.section_size = f.read_UInt16()

        self.unk_header_size = f.read_UInt16()  # 8
        self.unk_section_size = f.read_UInt16()
        self.constant = f.read_UInt32()
        self.unk1 = [f.read_UInt16() for _ in range(self.tex_count)]
        self.unk2 = [f.read_UInt16() for _ in range(self.tex_count)]

        self.info_header_size = f.read_UInt16()  # 8? Should be 4?
        self.info_section_size = f.read_UInt16()
        self.parameters = [TexParameters(f) for _ in range(self.tex_count)]

        self.names = [
            f.read(0x10).strip(b"\x00").decode() for _ in range(self.tex_count)
        ]

        for i in range(self.tex_count):
            self.parameters[i].unk4 = self.unk1[i]
            self.parameters[i].unk5 = self.unk2[i]
            self.parameters[i].name = self.names[i]

        self.name_map = {params.name: idx for idx, params in enumerate(self.parameters)}


class TexParameters:
    compression_info_offset: int
    format: TexFormat
    unk4: int
    unk5: int
    name: str

    def __init__(self, f: EndianBinaryReader):
        self.tex_offset = f.read_UInt16()
        self.parameters = f.read_UInt16()
        self.width2 = f.read_UInt8()
        self.unk1 = f.read_UInt8()
        self.unk2 = f.read_UInt8()
        self.unk3 = f.read_UInt8()

        self.coord_transform = self.parameters & 14
        self.color = (self.parameters >> 13) & 1
        self.format_code = (self.parameters >> 10) & 7
        self.format = TexFormat(self.format_code)

        self.height = 8 << ((self.parameters >> 7) & 7)
        self.width = 8 << ((self.parameters >> 4) & 7)
        self.flip_y = (self.parameters >> 3) & 1
        self.flip_x = (self.parameters >> 2) & 1
        self.repeat_y = (self.parameters >> 1) & 1
        self.repeat_x = self.parameters & 1

        if self.width == 0:
            if self.unk1 & 3 == 2:
                self.width = 0x200
            else:
                self.width = 0x100

        if self.height == 0:
            if (self.unk1 >> 4) & 3 == 2:
                self.height = 0x200
            else:
                self.height = 0x100


class PaletteInfo:
    def __init__(self, f: EndianBinaryReader):
        self.unk = f.read_UInt8()
        self.pal_count = f.read_UInt8()
        self.section_size = f.read_UInt16()

        self.unk_header_size = f.read_UInt16()  # 8
        self.unk_section_size = f.read_UInt16()
        self.constant = f.read_UInt32()
        self.unk1 = [f.read_UInt16() for _ in range(self.pal_count)]
        self.unk2 = [f.read_UInt16() for _ in range(self.pal_count)]

        self.info_header_size = f.read_UInt16()  # 8
        self.info_section_size = f.read_UInt16()
        self.parameters = [PaletteParameters(f) for _ in range(self.pal_count)]

        self.names = [
            f.read(0x10).strip(b"\x00").decode() for _ in range(self.pal_count)
        ]

        for i in range(self.pal_count):
            self.parameters[i].unk1 = self.unk1[i]
            self.parameters[i].unk2 = self.unk2[i]
            self.parameters[i].name = self.names[i]

        self.name_map = {params.name: idx for idx, params in enumerate(self.parameters)}


class PaletteParameters:
    unk1: int
    unk2: int
    name: str

    def __init__(self, f: EndianBinaryReader):
        self.pal_offset = f.read_UInt16() & 0x1FFF
        self.padding = f.read_UInt16()


def texel_decompress(
    data: bytes, info: bytes, colors: list[PaletteColor], im_size: tuple[int, int]
) -> Tuple[bytearray, List[PaletteColor]]:
    # TODO: remove palette stuff in this and move the function in the models folder

    def get_rgb(pal_index: int):
        return colors[pal_index].to_int_list()

    def sum_colors(colors1: list[int], colors2: list[int], w1: int, w2: int):
        return [
            (colors1[0] * w1 + colors2[0] * w2) // (w1 + w2),  # R
            (colors1[1] * w1 + colors2[1] * w2) // (w1 + w2),  # G
            (colors1[2] * w1 + colors2[2] * w2) // (w1 + w2),  # B
        ]

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
            if pal_idx_start > len(colors):
                pal_idx_start -= pal_offset * 2
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
    out_colors: List[PaletteColor] = []
    for _colors in new_colors:
        out_colors.append(PaletteColor.from_list(_colors))
    return out_data, out_colors
