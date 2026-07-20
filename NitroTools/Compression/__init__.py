from .lz10 import decompress_lz10, decompress_raw_lz10, compress_lz10, compress_raw_lz10
from .lz11 import decompress_lz11, decompress_raw_lz11, compress_lz11, compress_raw_lz11
from .rle import decompress_rle, decompress_raw_rle, compress_rle, compress_raw_rle
from .huffman import (
    decompress_huffman4bits,
    decompress_raw_huffman4bits,
    decompress_huffman8bits,
    decompress_raw_huffman8bits,
    compress_huffman4bits,
    compress_raw_huffman4bits,
    compress_huffman8bits,
    compress_raw_huffman8bits,
)
from pathlib import Path


def decompress(in_data: bytes):
    match in_data[0]:
        case 0x10:
            return decompress_lz10(in_data), "lz10"
        case 0x11:
            return decompress_lz11(in_data), "lz11"
        case 0x24:
            return decompress_huffman4bits(in_data), "huff4"
        case 0x28:
            return decompress_huffman8bits(in_data), "huff8"
        case 0x30:
            return decompress_rle(in_data), "rle"
        case _:
            raise Exception(f"Unsupported compression flag: {hex(in_data[0])}")


def compress(in_data: bytes, code: "str"):
    match code:
        case "lz10":
            return compress_lz10(in_data)
        case "lz11":
            return compress_lz11(in_data)
        case "huff4":
            return compress_huffman4bits(in_data)
        case "huff8":
            return compress_huffman8bits(in_data)
        case "rle":
            return compress_rle(in_data)
        case _:
            raise Exception(f"Unknown compression code: {code}")


def decompress_file(in_file: str, out_file: str = None):
    compressed_data = Path(in_file).read_bytes()
    decompressed_data, _ = decompress(compressed_data)
    if out_file:
        Path(out_file).write_bytes(decompressed_data)
        return
    Path(in_file).write_bytes(decompressed_data)
