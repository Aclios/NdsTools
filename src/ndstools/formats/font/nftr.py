from ndstools.fs import EndianBinaryReader
from ndstools.formats.file import File, NitroHeader
from ndstools.formats.graphics import RawBitmap, ImageCanva, Palette
from ndstools.formats.graphics.utils import new_bw_palette, empty_im

from enum import Enum
from typing import Optional

GLYPH_COLUMN_COUNT = 16
MAX_GLYPH_WIDTH = 16
MAX_GLYPH_HEIGHT = 16


class NFTREncoding(Enum):
    UTF_8 = 0
    UTF_16 = 1
    SHIFT_JIS = 2
    CP_1252 = 3


class NFTR(File):
    def read(self, f: EndianBinaryReader):
        self.header = NitroHeader(f, b"RTFN")
        self.finf = NFTR_FINF(f)
        f.seek(self.finf.cglp_offset)
        self.cglp = NFTR_CGLP(f)
        f.seek(self.finf.cwdh_offset)
        self.cwdh = NFTR_CWDH(f, self.cglp.glyph_count)
        f.seek(self.finf.cmap_offset)
        # TODO Cmap section

    def export_glyphs(self, out_path: str, palette: Optional[Palette] = None):
        row_count = self.cglp.glyph_count // GLYPH_COLUMN_COUNT
        if (self.cglp.glyph_count % GLYPH_COLUMN_COUNT) != 0:
            row_count += 1
        pal = palette if palette else new_bw_palette(self.cglp.bit_depth, inverted=True)
        im = empty_im(
            (GLYPH_COLUMN_COUNT * MAX_GLYPH_WIDTH, row_count * MAX_GLYPH_HEIGHT),
            pal.get_colors(),
            self.cglp.bit_depth,
            True,
        )
        glyph_canva = ImageCanva(
            palette=pal,
            im_size=(self.cglp.glyph_width, self.cglp.glyph_height),
            bit_depth=self.cglp.bit_depth,
            linear=True,
            transparency=True,
        )
        for idx, glyph_data in enumerate(self.cglp.glyphes_data):
            glyph_canva.load_bitmap(RawBitmap(glyph_data, try_decompress=False))
            glyph_canva.resolve()
            im.paste(
                glyph_canva.image,
                (
                    MAX_GLYPH_WIDTH * (idx % GLYPH_COLUMN_COUNT),
                    MAX_GLYPH_HEIGHT * (idx // GLYPH_COLUMN_COUNT),
                ),
            )
        im.save(out_path)


class NFTR_FINF:
    """
    NFTR File Info
    """

    def __init__(self, f: EndianBinaryReader):
        self.magic = f.check_magic(b"FNIF")
        self.section_size = f.read_UInt32()
        self.unk1 = f.read_UInt8()
        self.height = f.read_UInt8()
        self.null_char_index = f.read_UInt16()
        self.unk2 = f.read_UInt8()
        self.width = f.read_UInt8()
        self.width2 = f.read_UInt8()
        self.encoding = NFTREncoding(f.read_UInt8())
        self.cglp_offset = f.read_UInt32() - 8
        self.cwdh_offset = f.read_UInt32() - 8
        self.cmap_offset = f.read_UInt32() - 8
        if self.section_size == 0x20:
            self.glyph_height = f.read_UInt8()
            self.glyph_width = f.read_UInt8()
            self.bearing_y = f.read_UInt8()
            self.bearing_x = f.read_UInt8()


class NFTR_CGLP:
    """
    NFTR Characters Glyphs
    """

    def __init__(self, f: EndianBinaryReader):
        self.magic = f.check_magic(b"PLGC")
        self.section_size = f.read_UInt32()
        self.glyph_width = f.read_UInt8()
        self.glyph_height = f.read_UInt8()
        self.glyph_data_size = f.read_UInt16()
        self.unk = f.read_UInt16()
        self.bit_depth = f.read_UInt8()
        self.rotation = f.read_UInt8()
        self.glyph_count = (self.section_size - 0x10) // self.glyph_data_size
        self.glyphes_data = [
            f.read(self.glyph_data_size) for _ in range(self.glyph_count)
        ]


class NFTR_CWDH:
    """
    NFTR Characters Widths
    """

    def __init__(self, f: EndianBinaryReader, glyph_count: int):
        self.magic = f.check_magic(b"HDWC")
        self.section_size = f.read_UInt32()
        self.first_index = f.read_UInt16()
        self.last_index = f.read_UInt16()
        self.unk = f.read_UInt32()
        self.info = [GlyphInfo(f) for _ in range(glyph_count)]


class GlyphInfo:
    def __init__(self, f: EndianBinaryReader):
        self.x_offset = f.read_Int8()
        self.width = f.read_UInt8()
        self.display_width = f.read_UInt8()
