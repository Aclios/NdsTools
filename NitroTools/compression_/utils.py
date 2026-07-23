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
from typing import Tuple, Literal

type CompressionCode = Literal["lz10", "lz11", "huff4", "huff8", "rle"]
"""
The codes corresponding to NDS standard compressions and used in the following functions.
"""


def decompress(in_data: bytes) -> Tuple[bytes, CompressionCode]:
    """
    Decompress the compressed input bytes.
    These bytes must start with the standard NDS compression header.

    Returns:
        A tuple containing the decompressed data and the code of the compression
        method the data was compressed with.
    """
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


def decompress_raw(in_data: bytes, code: CompressionCode, decompressed_size: int):
    """
    Decompress the compressed input bytes using the compression method
    corresponding to code and the decompressed size.

    Returns:
        The decompressed data.
    """
    match code:
        case "lz10":
            return decompress_raw_lz10(in_data, decompressed_size)
        case "lz11":
            return decompress_raw_lz11(in_data, decompressed_size)
        case "huff4":
            return decompress_raw_huffman4bits(in_data, decompressed_size)
        case "huff8":
            return decompress_raw_huffman8bits(in_data, decompressed_size)
        case "rle":
            return decompress_raw_rle(in_data, decompressed_size)
        case _:
            raise Exception(f"Unknown compression code: {code}")


def compress(in_data: bytes, code: CompressionCode) -> bytearray:
    """
    Compress the input bytes using the compression method
    corresponding to code.

    Returns:
        The compressed data with the standard NDS compression header.
    """
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


def compress_raw(in_data: bytes, code: CompressionCode) -> bytearray:
    """
    Compress the input bytes using the compression method
    corresponding to code.

    Returns:
        The compressed data.
    """
    match code:
        case "lz10":
            return compress_raw_lz10(in_data)
        case "lz11":
            return compress_raw_lz11(in_data)
        case "huff4":
            return compress_raw_huffman4bits(in_data)
        case "huff8":
            return compress_raw_huffman8bits(in_data)
        case "rle":
            return compress_raw_rle(in_data)
        case _:
            raise Exception(f"Unknown compression code: {code}")
