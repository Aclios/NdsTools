from ndstools.fs import EndianBinaryReader
from ndstools.formats.file import File, NitroHeader
from .tex0 import TEX0


class NSBMD(File):
    def read(self, f: EndianBinaryReader):
        self.header = NitroHeader(f, b"BMD0")
        self.mdl_offset = f.read_UInt32()
        if self.header.section_count >= 2:
            self.tex_offset = f.read_UInt32()
        f.seek(self.mdl_offset)
        self.mdl = MDL0(f)
        if self.header.section_count >= 2:
            f.seek(self.tex_offset)
            self.tex = TEX0(f)

    def export_textures(self, out_dir: str):
        self.tex.export_textures(out_dir)


class MDL0:
    def __init__(self, f: EndianBinaryReader):
        self.magic = f.check_magic(b"MDL0")
        self.section_size = f.read_UInt32()
        self.data = f.read(self.section_size - 8)
