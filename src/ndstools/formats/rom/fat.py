from ndstools.fs import EndianBinaryStreamReader

from dataclasses import dataclass


@dataclass
class FAT_Entry:
    data_start_offset: int
    data_end_offset: int


class FAT:
    """
    The File Access Table contains pointers and sizes to the data of the files.
    """

    def __init__(self, data: bytes):
        file_count = len(data) // 8
        f = EndianBinaryStreamReader(data)
        self.files = [
            FAT_Entry(f.read_UInt32(), f.read_UInt32()) for _ in range(file_count)
        ]
