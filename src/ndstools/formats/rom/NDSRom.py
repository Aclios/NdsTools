from src.ndstools.fs import EndianBinaryReader, EndianBinaryStreamReader
from src.ndstools.formats.File import File

from pathlib import Path
from dataclasses import dataclass
from typing import List


class NDSRom(File):
    def read(self, f: EndianBinaryReader):
        self.name = f.read(12).decode().strip("\x00")
        self.game_code = f.read(4).decode()
        self.maker_code = f.read(2).decode()
        self.unit_code = f.read_UInt8()
        self.encryption_seed = f.read_UInt8()
        self.rom_size = f.read_UInt8()
        self.padding1 = f.read(8)
        self.region_code = f.read_UInt8()
        self.version = f.read_UInt8()
        self.autostart = f.read_UInt8()

        self.arm9_offset = f.read_UInt32()
        self.arm9_entry_adress = f.read_UInt32()
        self.arm9_ram_address = f.read_UInt32()
        self.arm9_data_size = f.read_UInt32()

        self.arm7_offset = f.read_UInt32()
        self.arm7_entry_adress = f.read_UInt32()
        self.arm7_ram_address = f.read_UInt32()
        self.arm7_data_size = f.read_UInt32()

        self.fnt_offset = f.read_UInt32()
        self.fnt_size = f.read_UInt32()

        self.fat_offset = f.read_UInt32()
        self.fat_size = f.read_UInt32()

        self.file_count = self.fat_size // 8

        self.arm9_ov_table_offset = f.read_UInt32()
        self.arm9_ov_table_size = f.read_UInt32()

        self.arm7_ov_table_offset = f.read_UInt32()
        self.arm7_ov_table_size = f.read_UInt32()

        self.arm9_data = f.read_data_at(self.arm9_offset, self.arm9_data_size)
        self.arm7_data = f.read_data_at(self.arm7_offset, self.arm7_data_size)

        self.fnt_data = f.read_data_at(self.fnt_offset, self.fnt_size)
        self.fnt = FNT(self.fnt_data)

        self.fat_data = f.read_data_at(self.fat_offset, self.fat_size)
        self.fat = FAT(self.fat_data)

        self.arm9_ov_table_data = f.read_data_at(
            self.arm9_ov_table_offset, self.arm9_ov_table_size
        )
        f.seek(self.arm9_ov_table_offset)
        self.overlay9 = [
            Overlay(f) for _ in range(len(self.arm9_ov_table_data) // 0x20)
        ]

        self.arm7_ov_table_data = f.read_data_at(
            self.arm7_ov_table_offset, self.arm7_ov_table_size
        )
        f.seek(self.arm7_ov_table_offset)
        self.overlay7 = [
            Overlay(f) for _ in range(len(self.arm7_ov_table_data) // 0x20)
        ]

        self.load_files_and_overlays(f)

    def load_files_and_overlays(self, f: EndianBinaryReader):
        self.files: List[ROMFile] = []
        for file in self.fnt.files:
            file_access = self.fat.files[file.idx]
            f.seek(file_access.data_start_offset)
            data = f.read(file_access.data_end_offset - file_access.data_start_offset)
            self.files.append(ROMFile(file.path, data))

        for overlay9 in self.overlay9:
            file_access = self.fat.files[overlay9.fat_idx]
            f.seek(file_access.data_start_offset)
            overlay9.data = f.read(
                file_access.data_end_offset - file_access.data_start_offset
            )

        for overlay7 in self.overlay7:
            file_access = self.fat.files[overlay7.fat_idx]
            f.seek(file_access.data_start_offset)
            overlay7.data = f.read(
                file_access.data_end_offset - file_access.data_start_offset
            )

    def extract_data(self, out_dir: str):
        code_dir = Path(out_dir, "code")
        dump_dir = Path(out_dir, "dump")
        files_dir = Path(out_dir, "files")

        code_dir.mkdir(exist_ok=True, parents=True)
        Path(code_dir, "arm9.bin").write_bytes(self.arm9_data)
        Path(code_dir, "arm7.bin").write_bytes(self.arm7_data)

        dump_dir.mkdir(exist_ok=True, parents=True)
        Path(dump_dir, "fat.bin").write_bytes(self.fat_data)
        Path(dump_dir, "fnt.bin").write_bytes(self.fnt_data)
        Path(dump_dir, "overlay9_table.bin").write_bytes(self.arm9_ov_table_data)
        Path(dump_dir, "overlay7_table.bin").write_bytes(self.arm7_ov_table_data)

        files_dir.mkdir(exist_ok=True, parents=True)
        for file in self.files:
            filepath = Path(out_dir, "files", file.path)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_bytes(file.data)

        for overlay9 in self.overlay9:
            Path(code_dir, f"overlay_{overlay9.idx:04d}.bin").write_bytes(overlay9.data)

        for overlay7 in self.overlay7:
            Path(code_dir, f"overlay_{overlay7.idx:04d}.bin").write_bytes(overlay7.data)


class FAT:
    def __init__(self, data: bytes):
        file_count = len(data) // 8
        f = EndianBinaryStreamReader(data)
        self.files = [
            FAT_Entry(f.read_UInt32(), f.read_UInt32()) for _ in range(file_count)
        ]


@dataclass
class FAT_Entry:
    data_start_offset: int
    data_end_offset: int


@dataclass
class FNT_File:
    path: Path
    idx: int


@dataclass
class ROMFile:
    path: Path
    data: bytes


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
        self._resolve_directory(self.directories[0], ".")

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


class Overlay:
    data: bytes

    def __init__(self, f: EndianBinaryReader):
        self.idx = f.read_UInt32()
        self.ram_adress = f.read_UInt32()
        self.data_size = f.read_UInt32()
        self.bss_size = f.read_UInt32()
        self.static_init_start = f.read_UInt32()
        self.static_init_end = f.read_UInt32()
        self.fat_idx = f.read_UInt32()
        compressed_data = f.read_UInt32()
        self.is_compressed = bool(compressed_data >> 24)
        self.decompressed_size = compressed_data & 0xFF_FF_FF
