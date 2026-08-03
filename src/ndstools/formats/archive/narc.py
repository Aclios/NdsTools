from ndstools.formats.file import File, NitroHeader
from ndstools.fs import EndianBinaryReader
from ndstools.formats.rom.fnt import FNT
from ndstools.formats.rom.fat import FAT

from pathlib import Path
from dataclasses import dataclass


@dataclass
class NARCFile:
    path: Path
    data: bytes


class NARC(File):
    """
    Load an NARC (for Nitro ARChive) file, which contains folders and files.

    :params inp: The input can either be an active EndianBinaryReader (if you want to read from an opened file),
        a bytes or bytearray stream, or a path to a file in your system.
    """

    def read(self, f: EndianBinaryReader):
        self.files: list[NARCFile] = []
        self.header = NitroHeader(f, b"NARC")
        assert self.header.section_count == 3
        self.fatb = NARC_FATB(f)
        self.fntb = NARC_FNTB(f)
        self.fimg = NARC_FIMG(f)
        self._load_files()

    def _get_file_data(self, file_idx: int):
        data_start = self.fatb.fat.files[file_idx].data_start_offset
        data_end = self.fatb.fat.files[file_idx].data_end_offset
        return self.fimg.data[data_start:data_end]

    def _load_files(self):
        if not self.fntb.is_empty:
            for file in self.fntb.fnt.files:
                data = self._get_file_data(file.idx)
                self.files.append(NARCFile(file.path, data))
        else:
            for idx in range(self.fatb.file_count):
                data = self._get_file_data(idx)
                self.files.append(NARCFile(f"{idx:04d}.bin", data))

    def export_files(self, out_dir: str):
        """
        Write the files of the NARC using the given directory as root.
        """
        for file in self.files:
            out_path = Path(out_dir, file.path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(file.data)


class NARC_FATB:
    def __init__(self, f: EndianBinaryReader):
        self.magic = f.check_magic(b"BTAF")
        self.section_size = f.read_UInt32()
        self.file_count = f.read_UInt32()
        self.fat_data = f.read(self.section_size - 12)
        self.fat = FAT(self.fat_data)


class NARC_FNTB:
    def __init__(self, f: EndianBinaryReader):
        self.magic = f.check_magic(b"BTNF")
        self.section_size = f.read_UInt32()
        self.fnt_data = f.read(self.section_size - 8)
        self.fnt = FNT(self.fnt_data)
        self.is_empty = self.fnt.is_empty


class NARC_FIMG:
    def __init__(self, f: EndianBinaryReader):
        self.magic = f.check_magic(b"GMIF")
        self.entry_size = f.read_UInt32()
        self.data = f.read(self.entry_size - 8)
        if len(self.data) < self.entry_size - 8:
            raise Exception("Error: NARC data ends earlier than excepted.")
