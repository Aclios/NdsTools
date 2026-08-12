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
    A NARC (for Nitro ARChive) file is an archive containing folders and files.
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
        Write the files contained inside the NARC archive, using out_dir as the root directory.
        """
        for file in self.files:
            out_path = Path(out_dir, file.path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(file.data)


class NARC_FATB:
    """
    The FATB section contains the number of files in the archive and FAT (File Access Table) data.
    """

    def __init__(self, f: EndianBinaryReader):
        self.magic = f.check_magic(b"BTAF")
        self.section_size = f.read_UInt32()
        self.file_count = f.read_UInt32()
        self.fat_data = f.read(self.section_size - 12)
        self.fat = FAT(self.fat_data)


class NARC_FNTB:
    """
    The FNTB section contains FNT (File Name Table) data. The FNT can be empty, in this case the files don't have names and are only referenced by their ids.
    """

    def __init__(self, f: EndianBinaryReader):

        self.magic = f.check_magic(b"BTNF")
        self.section_size = f.read_UInt32()
        self.fnt_data = f.read(self.section_size - 8)
        self.fnt = FNT(self.fnt_data)
        self.is_empty = self.fnt.is_empty


class NARC_FIMG:
    """
    The FIMG section contains the raw files data.
    """

    def __init__(self, f: EndianBinaryReader):
        self.magic = f.check_magic(b"GMIF")
        self.entry_size = f.read_UInt32()
        self.data = f.read(self.entry_size - 8)
        if len(self.data) < self.entry_size - 8:
            raise Exception("Error: NARC data ends earlier than excepted.")
