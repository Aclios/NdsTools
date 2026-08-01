from ndstools.fs import EndianBinaryReader
from ndstools.compression import decompress_blz


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

    def get_data(self, decompress: bool = True):
        if self.is_compressed and decompress:
            return decompress_blz(self.data)
        return self.data
