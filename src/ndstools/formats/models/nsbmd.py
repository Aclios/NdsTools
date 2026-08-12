from ndstools.fs import EndianBinaryReader
from ndstools.formats.file import File, NitroHeader
from .tex0 import TEX0


class NSBMD(File):
    """
    A NSBMD (Nitro Binary MoDel) contains a 3D model, and optionaly textures for this model.

    Parsing of the 3D model data isn't currently supported, but textures can be exported.
    """

    def __repr__(self):
        return self.tex.__repr__()

    def read(self, f: EndianBinaryReader):
        self.header = NitroHeader(f, b"BMD0")
        self.mdl_offset = f.read_UInt32()
        if self.header.section_count >= 2:
            self.tex_offset = f.read_UInt32()
        f.seek(self.mdl_offset)
        self.mdl = MDL0(f)
        self.tex = None
        if self.header.section_count >= 2:
            f.seek(self.tex_offset)
            self.tex = TEX0(f)

    def export_textures(self, out_dir: str):
        """
        Export textures to the given directory. Raise if the file doesn't contain textures.
        """
        if self.tex is None:
            raise Exception("This NSBMD file doesn't have a textures section.")
        self.tex.export_textures(out_dir)


class MDL0:
    def __init__(self, f: EndianBinaryReader):
        self.magic = f.check_magic(b"MDL0")
        self.section_size = f.read_UInt32()
        self.data = f.read(self.section_size - 8)
