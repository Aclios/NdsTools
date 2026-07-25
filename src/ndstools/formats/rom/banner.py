from src.ndstools.fs import EndianBinaryReader
from src.ndstools.formats.graphics import RawPalette, RawBitmap, ImageCanva

SUPPORTED_VERSIONS = [0x0001, 0x0002, 0x0003, 0x0103]


class UnsupportedVersion(Exception):
    pass


class Version1:
    size = 0x840
    has_chinese = False
    has_korean = False
    animated = False


class Version2:
    size = 0x940
    has_chinese = True
    has_korean = False
    animated = False


class Version3:
    size = 0x1240
    has_chinese = True
    has_korean = True
    animated = False


class VersionDSi:
    size = 0x23C0
    has_chinese = True
    has_korean = True
    animated = True


class NDSBanner:
    def __init__(self, f: EndianBinaryReader):
        self.version = f.read_UInt16()
        if not self.version in SUPPORTED_VERSIONS:
            raise UnsupportedVersion("Unsupported banner version")
        match self.version:
            case 0x0001:
                self.info = Version1()
            case 0x0002:
                self.info = Version2()
            case 0x0003:
                self.info = Version3()
            case 0x0103:
                self.info = VersionDSi()
        self.checksum = f.read_UInt16()
        self.padding = f.read(0x1C)
        self.bitmap = RawBitmap(f.read(0x200))
        self.palette = RawPalette(f.read(0x20))
        self.japanese = self.read_name(f)
        self.english = self.read_name(f)
        self.french = self.read_name(f)
        self.german = self.read_name(f)
        self.italian = self.read_name(f)
        self.spanish = self.read_name(f)
        if self.info.has_chinese:
            self.chinese = self.read_name(f)
        if self.info.has_korean:
            self.korean = self.read_name(f)

    @staticmethod
    def read_name(f: EndianBinaryReader):
        return f.read(0x100).decode("utf-16").strip("\0")

    def get_icon(self):
        canva = ImageCanva(
            Bitmap=self.bitmap, Palette=self.palette, bit_depth=4, im_size=(32, 32)
        )
        return canva.build_im()[0]
