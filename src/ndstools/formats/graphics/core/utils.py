import struct
from .constants import VALID_BIT_DEPTH


def verify_bit_depth(bit_depth: int):
    return bit_depth in VALID_BIT_DEPTH


def get_expected_data_size(size: tuple[int, int], bit_depth: int):
    w, h = size
    return w * h * bit_depth // 8


def get_expected_tile_count(size: tuple[int, int]):
    w, h = size
    if w % 8 != 0 or h % 8 != 0:
        raise Exception(
            "Image dimensions are not a multiple of zero. Are you sure it's tiled?"
        )
    return (w // 8) * (h // 8)


def eightbpp_to_fourbpp(data: bytes | bytearray):
    newdata = bytearray()
    it = iter(data)
    for _ in range(len(data) // 2):
        val1 = next(it) % 0x10
        val2 = next(it) % 0x10
        newdata += struct.pack("<B", val2 * 0x10 + val1)
    return newdata


def fourbpp_to_eightbpp(data: bytes | bytearray, pal_idx: int = 0):
    newdata = bytearray()
    for val in data:
        p1 = (val % 0x10) + (0x10 * pal_idx)
        p2 = (val // 0x10) + (0x10 * pal_idx)
        newdata += struct.pack("<B", p1) + struct.pack("<B", p2)
    return newdata


def twobpp_to_eightbpp(data: bytes | bytearray, pal_idx: int = 0):
    newdata = bytearray()
    for val in data:
        p1 = (val & 0x3) + (0x4 * pal_idx)
        p2 = ((val >> 2) & 0x3) + (0x4 * pal_idx)
        p3 = ((val >> 4) & 0x3) + (0x4 * pal_idx)
        p4 = ((val >> 6) & 0x3) + (0x4 * pal_idx)
        newdata += (
            struct.pack("<B", p4)
            + struct.pack("<B", p3)
            + struct.pack("<B", p2)
            + struct.pack("<B", p1)
        )
    return newdata


def eightbpp_to_twobpp(data: bytes | bytearray):
    newdata = bytearray()
    it = iter(data)
    for _ in range(len(data) // 4):
        val1 = next(it) % 0x4
        val2 = next(it) % 0x4
        val3 = next(it) % 0x4
        val4 = next(it) % 0x4
        newdata += struct.pack("<B", (val4 << 6) + (val3 << 4) + (val2 << 2) + val1)
    return newdata


def convert_from_eightbpp(data: bytes | bytearray, bit_depth: int):
    """
    Convert an 8 bytes per pixel data stream to an N bytes per pixel data stream, with N in [2, 4, 8].

    :params data: A bytes stream.
    :params bit_depth: The bit depth the new stream should have.

    :returns: A new stream with the given bit depth.
    """
    assert bit_depth in [2, 4, 8]
    if bit_depth == 2:
        return eightbpp_to_twobpp(data)
    elif bit_depth == 4:
        return eightbpp_to_fourbpp(data)
    else:
        return data


def convert_to_eightbpp(data: bytes | bytearray, bit_depth: int, pal_idx: int = 0):
    """
    Convert an N bytes per pixel data stream to an 8 bytes per pixel data stream, with N in [2, 4, 8].

    :params data: A bytes stream.
    :params bit_depth: The bit depth the new stream should have.
    :params pal_idx: The palette idx the pixels should be pushed to. For example, if you convert a 4bpp stream to 8bpp with pal_idx = 1, the pixels with be written with values between 0x10 and 0x20.
    :returns: A new stream with a bit depth of 8.
    """
    assert bit_depth in [2, 4, 8]
    if bit_depth == 2:
        return twobpp_to_eightbpp(data, pal_idx)
    elif bit_depth == 4:
        return fourbpp_to_eightbpp(data, pal_idx)
    else:
        return data


def code_to_bit_depth(bit_depth_code: int):
    match bit_depth_code:
        case 1:
            return 1
        case 2:
            return 2
        case 3:
            return 4
        case 4:
            return 8
        case _:
            raise Exception("Input is not a valid code for bit depth.")


def bit_depth_to_code(bit_depth: int):
    match bit_depth:
        case 1:
            return 1
        case 2:
            return 2
        case 4:
            return 3
        case 8:
            return 4
        case _:
            raise Exception("Input is not a valid bit depth.")
