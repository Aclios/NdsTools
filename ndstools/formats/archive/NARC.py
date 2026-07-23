from ndstools.formats.File import File, NitroHeader
from ndstools.fs import EndianBinaryReader

from pathlib import Path
from dataclasses import dataclass


class FNTB_Directory:
    _curr_file_idx: int

    def __init__(self, f: EndianBinaryReader, base_offset: int):
        self.offset = f.read_UInt32()
        self.file_start_idx = f.read_UInt16()
        self.children_dir_count = f.read_UInt16() & 0xFFF
        pos = f.tell()
        f.seek(base_offset + self.offset)
        self.children: list[FNTB_Child] = []
        lookup = f.peek(1)
        while int.from_bytes(lookup):
            self.children.append(FNTB_Child(f))
            lookup = f.peek(1)
        f.seek(pos)

    def has_sub_directories(self):
        return any(child.is_dir for child in self.children)


class FNTB_Child:
    def __init__(self, f: EndianBinaryReader):
        self.next_id = None
        chunk = f.read_UInt8()
        self.name_size = chunk & 0x7F
        self.is_dir = bool(chunk >> 7)
        self.name = f.read(self.name_size).decode("shift-jis-2004")
        if self.is_dir:
            self.next_id = f.read_UInt16() & 0xFFF


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
        self._resolve_filetree()

    def _resolve_filetree(self):
        self._resolve_directory(self.fntb.directories[0], ".")

    def _resolve_directory(self, dir: FNTB_Directory, current_path: Path):
        dir._curr_file_idx = dir.file_start_idx
        for child in dir.children:
            if child.is_dir:
                new_dir = self.fntb.directories[child.next_id]
                self._resolve_directory(new_dir, Path(current_path, child.name))
            else:
                self.files.append(
                    NARCFile(
                        Path(current_path, child.name),
                        self._get_file_data(dir._curr_file_idx),
                    )
                )
                dir._curr_file_idx += 1

    def _get_file_data(self, file_idx: int):
        data_start = self.fatb.file_starts[file_idx]
        data_end = self.fatb.file_ends[file_idx]
        return self.fimg.data[data_start:data_end]

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
        self.file_starts: list[int] = []
        self.file_ends: list[int] = []
        for _ in range(self.file_count):
            self.file_starts.append(f.read_UInt32())
            self.file_ends.append(f.read_UInt32())


class NARC_FNTB:
    def __init__(self, f: EndianBinaryReader):
        base_offset = f.tell()
        self.magic = f.check_magic(b"BTNF")
        self.section_size = f.read_UInt32()
        first_offset = int.from_bytes(f.peek(4), "little")
        self.entry_count = first_offset // 8
        self.directories = [
            FNTB_Directory(f, base_offset + 8) for _ in range(self.entry_count)
        ]
        f.seek(base_offset + self.section_size)


class NARC_FIMG:
    def __init__(self, f: EndianBinaryReader):
        self.magic = f.check_magic(b"GMIF")
        self.entry_size = f.read_UInt32()
        self.data = f.read(self.entry_size - 8)
        if len(self.data) < self.entry_size - 8:
            raise Exception("Error: NARC data ends earlier than excepted.")


@dataclass
class NARCFile:
    path: Path
    data: bytes
