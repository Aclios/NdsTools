from NitroTools.fs import (
    EndianBinaryReader,
    EndianBinaryFileReader,
    EndianBinaryStreamReader,
    EndianBinaryStreamWriter,
)
from pathlib import Path
from NitroTools.compression import decompress, compress

FileInput = EndianBinaryReader | bytes | bytearray | str | Path


class File:
    def __init__(self, inp: FileInput, no_decompress=False):
        self.compression = None
        if isinstance(inp, (str, Path)):
            data = EndianBinaryFileReader(inp).read()

        elif isinstance(inp, EndianBinaryReader):
            data = inp.read()

        elif isinstance(inp, (bytes, bytearray)):
            data = inp

        else:
            raise Exception("Invalid input. Expected a buffer or a filepath.")
        if not no_decompress:
            try:
                data, compression = decompress(data)
                self.compression = compression
            except:
                pass

        self.read(EndianBinaryStreamReader(data))

    def read(self, f: EndianBinaryReader):
        """
        Reads the file and loads its data to the file object. Must be overwritten.
        """
        raise Exception("The read method must be overwritten")

    def to_bytes(self) -> bytes:
        """
        Returns the file data as bytes.
        """
        raise Exception("The to_bytes method must be overwritten")

    def write(self, filepath: str | Path) -> None:
        """
        Write the file to the given filepath.

        :param filepath: The destination filepath.
        """
        if self.compression:
            open(filepath, mode="wb").write(compress(self.to_bytes(), self.compression))
        else:
            open(filepath, mode="wb").write(self.to_bytes())


class NitroHeader:
    def __init__(self, f: EndianBinaryReader, magic: bytes):
        self.magic = f.check_magic(magic)
        self.unk = f.read_UInt32()
        self.filesize = f.read_UInt32()
        self.header_size = f.read_UInt16()
        self.section_count = f.read_UInt16()

    def to_bytes(self):
        stream = EndianBinaryStreamWriter()
        stream.write(self.magic)
        stream.write_UInt32(self.unk)
        stream.write_UInt32(self.filesize)
        stream.write_UInt16(self.header_size)
        stream.write_UInt16(self.section_count)
        return stream.getvalue()
