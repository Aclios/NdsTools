from ndstools.fs import EndianBinaryStreamReader
from .lz10 import decompress_raw_lz10


class DecompressionError(ValueError):
    pass


def decompress_blz(data: bytes):
    """
    Decompress data using the backward-LZ algorithm.

    Likely only relevant for arm9 code and overlays.
    """
    f = EndianBinaryStreamReader(data)
    f.seek(-8, 2)
    compression_info = f.read_UInt32()
    extra_size = f.read_UInt32()
    if extra_size == 0:
        raise DecompressionError("Input data isn't blz-compressed.")
    header_size = compression_info >> 24
    compressed_data_size = compression_info & 0xFF_FF_FF
    compressed_data = data[-compressed_data_size:-header_size]
    compressed_data = bytearray(compressed_data)
    # FIXME: don't do that?
    compressed_data.reverse()
    decompressed_data = decompress_raw_lz10(
        compressed_data, compressed_data_size + extra_size, disp_extra=3
    )
    decompressed_data.reverse()
    start_data = data[:-compressed_data_size]
    out_data = start_data + decompressed_data
    return out_data
