from src.ndstools.fs import EndianBinaryReader
from src.ndstools.formats.file import File, NitroHeader
from .swav import AudioData

from pathlib import Path


class SWAR(File):
    """
    A SWAR file is an archive for sound effects.
    """

    def read(self, f: EndianBinaryReader):
        self.header = NitroHeader(f, b"SWAR")
        self.data = SWAR_DATA(f)

    def extract(self, out_dir: str):
        Path(out_dir).mkdir(exist_ok=True, parents=True)
        for idx, entry in enumerate(self.data.entries):
            entry.to_wav(Path(out_dir) / f"swav_{idx}.wav")


class SWAR_DATA:
    def __init__(self, f: EndianBinaryReader):
        f.check_magic(b"DATA")
        self.size = f.read_Int32()
        padding = f.read(0x20)
        self.entry_count = f.read_Int32()
        self.entry_offsets = [f.read_Int32() for _ in range(self.entry_count)]
        self.entry_size = []
        for i in range(self.entry_count - 1):
            self.entry_size.append(self.entry_offsets[i + 1] - self.entry_offsets[i])
        if self.entry_count > 0:
            self.entry_size.append(self.size - self.entry_offsets[-1])
        self.entries: list[AudioData] = []
        for i in range(self.entry_count):
            f.seek(self.entry_offsets[i])
            self.entries.append(AudioData(f, self.entry_size[i]))
