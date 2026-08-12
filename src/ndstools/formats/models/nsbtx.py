from ndstools.fs import EndianBinaryReader
from ndstools.formats.file import File, NitroHeader
from .tex0 import TEX0


class NSBTX(File):
    """
    A NSBTX (Nitro Binary TeXtures) contains textures for 3D models.
    """

    def read(self, f: EndianBinaryReader):
        self.header = NitroHeader(f, b"BTX0")
        self.tex_offset = f.read_UInt32()
        f.seek(self.tex_offset)
        self.tex = TEX0(f)

    def export_textures(self, out_dir: str):
        """
        Export textures to the given directory.
        """
        self.tex.export_textures(out_dir)
