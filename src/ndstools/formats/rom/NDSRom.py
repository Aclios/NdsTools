from src.ndstools.fs import EndianBinaryReader
from src.ndstools.formats.File import File
from .FNT_FAT import FNT, FAT
from .overlay import Overlay

from pathlib import Path
from dataclasses import dataclass
from typing import List


@dataclass
class ROMFile:
    path: Path
    data: bytes


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

        self._load_files_and_overlays(f)

    def _get_file_data(self, f: EndianBinaryReader, file_idx: int) -> bytes:
        file_access = self.fat.files[file_idx]
        return f.read_data_at(
            file_access.data_start_offset,
            file_access.data_end_offset - file_access.data_start_offset,
        )

    def _load_files_and_overlays(self, f: EndianBinaryReader):
        self.files: List[ROMFile] = []
        for file in self.fnt.files:
            data = self._get_file_data(f, file.idx)
            self.files.append(ROMFile(file.path, data))

        for overlay in self.overlay9:
            overlay.data = self._get_file_data(f, overlay.fat_idx)

        for overlay in self.overlay7:
            overlay.data = self._get_file_data(f, overlay.fat_idx)

    def extract_all(self, out_dir: str):
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
            filepath = Path(files_dir, file.path)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_bytes(file.data)

        for overlay9 in self.overlay9:
            Path(code_dir, f"overlay_{overlay9.idx:04d}.bin").write_bytes(overlay9.data)

        for overlay7 in self.overlay7:
            Path(code_dir, f"overlay_{overlay7.idx:04d}.bin").write_bytes(overlay7.data)
