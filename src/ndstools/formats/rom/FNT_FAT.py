from src.ndstools.fs import EndianBinaryStreamReader, EndianBinaryReader

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class FAT_Entry:
    data_start_offset: int
    data_end_offset: int


class FAT:
    def __init__(self, data: bytes):
        file_count = len(data) // 8
        f = EndianBinaryStreamReader(data)
        self.files = [
            FAT_Entry(f.read_UInt32(), f.read_UInt32()) for _ in range(file_count)
        ]


@dataclass
class FNT_File:
    path: Path
    idx: int


class FNT_Directory:
    _curr_file_idx: int

    def __init__(self, f: EndianBinaryReader):
        self.offset = f.read_UInt32()
        self.file_start_idx = f.read_UInt16()
        self.children_dir_count = f.read_UInt16() & 0xFFF
        pos = f.tell()
        f.seek(self.offset)
        self.children: list[FNT_Child] = []
        lookup = f.peek(1)
        while int.from_bytes(lookup):
            self.children.append(FNT_Child(f))
            lookup = f.peek(1)
        f.seek(pos)


class FNT:
    def __init__(self, data: bytes):
        f = EndianBinaryStreamReader(data)
        first_offset = int.from_bytes(f.peek(4), "little")
        self.entry_count = first_offset // 8
        self.directories = [FNT_Directory(f) for _ in range(self.entry_count)]
        self.files: List[FNT_File] = []
        self._resolve_filetree()

    def _resolve_filetree(self):
        self._resolve_directory(self.directories[0], Path("."))

    def _resolve_directory(self, dir: FNT_Directory, current_path: Path):
        dir._curr_file_idx = dir.file_start_idx
        for child in dir.children:
            if child.is_dir:
                new_dir = self.directories[child.next_id]
                self._resolve_directory(new_dir, Path(current_path, child.name))
            else:
                self.files.append(
                    FNT_File(
                        Path(current_path, child.name),
                        dir._curr_file_idx,
                    )
                )
                dir._curr_file_idx += 1


class FNT_Child:
    def __init__(self, f: EndianBinaryReader):
        self.next_id = -1
        chunk = f.read_UInt8()
        self.name_size = chunk & 0x7F
        self.is_dir = bool(chunk >> 7)
        self.name = f.read(self.name_size).decode("shift-jis-2004")
        if self.is_dir:
            self.next_id = f.read_UInt16() & 0xFFF
