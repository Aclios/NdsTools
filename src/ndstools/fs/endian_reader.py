import struct
from io import BytesIO
from pathlib import Path


class EndianBinaryReader:
    def __init__(
        self, filepath: str | Path, endianness: str = "little"
    ):  # should be overwritten
        self.set_endianness(endianness)
        self.filepath = filepath
        self.file = open(self.filepath, mode="rb")
        self.read = self.file.read
        self.tell = self.file.tell
        self.seek = self.file.seek

    def set_endianness(self, endianness: str):
        if endianness == "little":
            self.endian_flag = "<"
        elif endianness == "big":
            self.endian_flag = ">"
        else:
            raise Exception(r"Unknown endianness : should be 'little' or 'big'")

    def read_Int8(self) -> int:
        return struct.unpack(f"{self.endian_flag}b", self.read(1))[0]

    def read_UInt8(self) -> int:
        return struct.unpack(f"{self.endian_flag}B", self.read(1))[0]

    def read_Int16(self) -> int:
        return struct.unpack(f"{self.endian_flag}h", self.read(2))[0]

    def read_UInt16(self) -> int:
        return struct.unpack(f"{self.endian_flag}H", self.read(2))[0]

    def read_Int32(self) -> int:
        return struct.unpack(f"{self.endian_flag}i", self.read(4))[0]

    def read_UInt32(self) -> int:
        return struct.unpack(f"{self.endian_flag}I", self.read(4))[0]

    def read_Int64(self) -> int:
        return struct.unpack(f"{self.endian_flag}q", self.read(8))[0]

    def read_UInt64(self) -> int:
        return struct.unpack(f"{self.endian_flag}Q", self.read(8))[0]

    def check_magic(self, magic: bytes) -> bytes:
        check = self.read(len(magic))
        if check != magic:
            raise Exception(
                f"Error: Invalid magic. Expected {str(magic)}, read {str(check)}"
            )
        return magic

    def peek(self, size: int = 0):
        val = self.read(size)
        self.seek(-size, 1)
        return val

    def read_string_until_null(self) -> bytes:
        data = b""
        byte = self.read(1)
        while byte != b"\x00":
            data += byte
            byte = self.read(1)
        return data

    def read_data_at(self, offset: int, size: int):
        self.seek(offset)
        return self.read(size)

    def align(self, alignment: int):
        mod = self.tell() % alignment
        if mod != 0:
            self.read(alignment - mod)

    def get_size(self):
        pos = self.tell()
        size = self.seek(0, 2)
        self.seek(pos)
        return size


class EndianBinaryFileReader(EndianBinaryReader):
    def __init__(self, filepath: str | Path, endianness: str = "little"):
        self.set_endianness(endianness)
        self.filepath = filepath
        self.file = open(self.filepath, mode="rb")
        self.read = self.file.read
        self.tell = self.file.tell
        self.seek = self.file.seek

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()


class EndianBinaryStreamReader(EndianBinaryReader):
    def __init__(self, stream: bytes, endianness: str = "little"):
        self.set_endianness(endianness)
        self.stream = BytesIO(stream)
        self.read = self.stream.read
        self.tell = self.stream.tell
        self.seek = self.stream.seek
        self.getvalue = self.stream.getvalue
