from ndstools.fs import EndianBinaryReader, EndianBinaryFileWriter
from ndstools.formats.file import File, NitroHeader
from .adpcm import decode_block


class SWAV(File):
    """
    A SWAV file contains a sound effect.
    """

    def read(self, f: EndianBinaryReader):
        self.header = NitroHeader(f, b"SWAV")
        assert self.header.section_count == 1
        self.data = SWAV_DATA(f)

    def export(self, out_path: str):
        self.data.audio.to_wav(out_path)


class SWAV_DATA:
    def __init__(self, f: EndianBinaryReader):
        self.magic = f.check_magic(b"DATA")
        self.section_size = f.read_UInt32()
        self.audio = AudioData(f, self.section_size - 0x14)


class AudioData:
    data: bytes

    def __init__(self, f: EndianBinaryReader, data_size: int):
        self.type = f.read_UInt8()
        self.loop = f.read_UInt8()
        self.samplerate = f.read_UInt16()
        self.time = f.read_UInt16()
        self.loop_offset = f.read_UInt16()
        self.nonloop_size = f.read_UInt32()
        self.data = f.read(data_size)

    def to_wav(self, out_filepath):
        if self.type == 0:  # PCM8
            write_pcm_wav(self.data, 8, self.samplerate, out_filepath)
        elif self.type == 1:  # PCM16
            write_pcm_wav(self.data, 16, self.samplerate, out_filepath)
        else:  # ADPCM
            decoded_data = decode_block(self.data)
            write_pcm_wav(decoded_data, 16, self.samplerate, out_filepath)


def write_pcm_wav(data: bytes | bytearray, pcm: int, samplerate: int, filepath: str):
    with EndianBinaryFileWriter(filepath) as f:
        assert pcm in [8, 16]
        f.write(b"RIFF")
        if pcm == 16:
            f.write_Int32(44 + len(data) - 8)
        elif pcm == 8:
            f.write_Int32(44 + 2 * len(data) - 8)
        f.write(b"WAVEfmt ")
        f.write_Int32(0x10)
        f.write_Int16(1)
        f.write_Int16(1)
        f.write_Int32(samplerate)
        f.write_Int32(samplerate * 0x10 // 8)
        f.write_Int16(0x10 // 8)
        f.write_Int16(0x10)
        f.write(b"data")
        if pcm == 16:
            f.write_Int32(len(data))
            f.write(data)
        elif pcm == 8:
            f.write_Int32(len(data) * 2)
            for byte in data:
                if byte > 0x80:
                    f.write_UInt8(1)
                else:
                    f.write_UInt8(0)
                f.write_UInt8(byte)
