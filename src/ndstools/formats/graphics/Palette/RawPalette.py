from src.ndstools.fs import EndianBinaryReader, EndianBinaryStreamWriter
from src.ndstools.formats.graphics.Palette.Palette import Palette, PaletteColor


class RawPalette(Palette):
    """
    Load a raw palette. It must be associated with at least a RawBitmap, and may require a RawTilemap.

    .. warning::
        If you pass an EndianBinaryReader, it will use all the data until the end of the file; if you pass a path,
        it will use the entirety of the data of the file. Read the file yourself and pass bytes/bytearray if this
        behavior is a problem.

    :params inp: The input can either be an active EndianBinaryReader (if you want to read from an opened file),
        a bytes or bytearray stream, or a path to a file in your system.
    """

    def read(self, f: EndianBinaryReader):
        f.seek(0, 2)
        self.color_count = f.tell() // 2
        f.seek(0)
        self.colors = [
            PaletteColor.from_bytes(f.read(2)) for _ in range(self.color_count)
        ]

    def get_colors(self):
        return self.colors

    def set_colors(self, colors: list[PaletteColor]):
        if len(self.colors) > 0x100:
            self.colors[:0x100] = colors
        else:
            self.colors = colors

    def to_bytes(self):
        f = EndianBinaryStreamWriter()
        for color in self.colors:
            f.write(color.to_bytes())
        return f.getvalue()
