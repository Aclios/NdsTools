from src.ndstools.formats.graphics import ImageCanva
from src.ndstools.formats.common import texel_decompress
from src.ndstools.fs import EndianBinaryReader
from src.ndstools.formats.graphics import RawBitmap, RawPalette

from pathlib import Path


class TEX0:
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

        for idx, _ in enumerate(self.tex_info.parameters):
            (
                self.tex_info.parameters[idx].bitmap_data,
                self.tex_info.parameters[idx].palette_data,
                self.tex_info.parameters[idx].compression_info_data,
            ) = self.get_texture(f, idx)

    def export_textures(self, out_dir: str):
        Path(out_dir).mkdir(exist_ok=True, parents=True)
        for idx in range(len(self.tex_info.parameters)):
            name = self.tex_info.names[idx]
            im = self.tex_info.parameters[idx].build_image()
            im.save(Path(out_dir) / (name.decode() + ".png"))

    def get_texture(self, f: EndianBinaryReader, tex_idx: int):
        assert tex_idx < len(
            self.tex_info.parameters
        ), f"Given idx ({tex_idx}) is beyond max tex idx ({len(self.tex_info.parameters)})"
        parameters = self.tex_info.parameters[tex_idx]
        if parameters.format_code != 5:
            bitmap_offset = (
                parameters.tex_offset * 8 + self.offset + self.tex_data_offset
            )
            f.seek(bitmap_offset)
            bitmap_data = f.read(
                parameters.width * parameters.height * parameters.format.bit_depth // 8
            )
        else:
            bitmap_offset = (
                self.offset
                + self.tex_compressed_data_offset
                + parameters.tex_offset * 0x8
            )
            f.seek(bitmap_offset)
            bitmap_data = f.read(parameters.width * parameters.height // 4)

        palette_offset = (
            self.offset
            + self.palette_data_offset
            + self.pal_info.parameters[tex_idx].pal_offset * 0x8
        )

        f.seek(palette_offset)
        if parameters.format_code != 5:
            palette_data = f.read(parameters.format.palette_size)
        else:
            palette_data = f.read(self.offset + self.section_size - palette_offset)

        if parameters.format_code == 5:
            compression_info_offset = (
                self.offset
                + self.tex_compressed_info_data_offset
                + parameters.compression_info_offset
            )
            f.seek(compression_info_offset)
            info_data = f.read(parameters.width * parameters.height // 8)
        else:
            info_data = bytes()

        return bitmap_data, palette_data, info_data

    def calculate_compression_info_offsets(self):
        compression_info_offset = 0
        for parameters in self.tex_info.parameters:
            if parameters.format_code == 5:
                parameters.compression_info_offset = compression_info_offset
                compression_info_offset += (parameters.width * parameters.height) // 8


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

        self.names = [f.read(0x10).strip(b"\x00") for _ in range(self.tex_count)]


class TexFormat:
    idx: int
    palette_size: int
    bit_depth: int


class TexParameters:
    bitmap_data: bytes
    palette_data: bytes
    compression_info_offset: int
    compression_info_data: bytes
    format: TexFormat

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
        match self.format_code:
            case 1:
                self.format = FormatA3I5()
            case 2:
                self.format = FormatI2()
            case 3:
                self.format = FormatI4()
            case 4:
                self.format = FormatI8()
            case 5:
                self.format = FormatTexel()
            case 6:
                self.format = FormatA5I3()
            case 7:
                self.format = FormatA1BGR555()
            case _:
                raise Exception(f"Unsupported texture format code: {self.format_code}")

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

    def build_image(self):
        transparency = False
        if self.format_code == 5:
            transparency = True
            palette = RawPalette(self.palette_data)
            data, new_colors = texel_decompress(
                self.bitmap_data,
                self.compression_info_data,
                palette.get_colors(),
                (self.width, self.height),
            )
            bitmap = RawBitmap(data)
            palette.set_colors(new_colors)
        else:
            bitmap = RawBitmap(self.bitmap_data)
            palette = RawPalette(self.palette_data)

        im = ImageCanva(
            Bitmap=bitmap,
            Palette=palette,
            bit_depth=self.format.bit_depth,
            im_size=(self.width, self.height),
            linear=True,
            transparency=transparency,
        )
        return im.build_im()[0]


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

        self.names = [f.read(0x10).strip(b"\x00") for _ in range(self.pal_count)]


class PaletteParameters:
    def __init__(self, f: EndianBinaryReader):
        self.pal_offset = f.read_UInt16() & 0x1FFF
        self.padding = f.read_UInt16()


class FormatA3I5(TexFormat):
    idx = 1
    palette_size = 0x40
    bit_depth = 8


class FormatI2(TexFormat):
    idx = 2
    palette_size = 0x8
    bit_depth = 2


class FormatI4(TexFormat):
    idx = 3
    palette_size = 0x20
    bit_depth = 4


class FormatI8(TexFormat):
    idx = 4
    palette_size = 0x200
    bit_depth = 8


class FormatTexel(TexFormat):
    idx = 5
    palette_size = 0x200
    bit_depth = 8


class FormatA5I3(TexFormat):
    idx = 6
    palette_size = 0x10
    bit_depth = 8


class FormatA1BGR555(TexFormat):
    idx = 7
    palette_size = 0
    bit_depth = 16
