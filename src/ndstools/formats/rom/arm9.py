from ndstools.fs import EndianBinaryReader
from ndstools.compression import decompress_blz


class ARM9:
    def __init__(
        self, f: EndianBinaryReader, info_offset: int, data_offset: int, data_size: int
    ):
        f.seek(info_offset)
        self.dtcm_ram_address = f.read_UInt32()
        self.itcm_ram_address = f.read_UInt32()
        self.end_ram_adress = f.read_UInt32()
        self.end_ram_adress2 = f.read_UInt32()
        self.unk_adress = f.read_UInt32()
        self.compression_info = f.read_UInt32()
        self.is_compressed = bool(self.compression_info)
        self.compressed_size = self.compression_info - 0x2_00_00_00
        self.data = f.read_data_at(data_offset, data_size)

    def get_data(self, decompress: bool = True):
        if self.is_compressed and decompress:
            return decompress_blz(self.data)
        return self.data
