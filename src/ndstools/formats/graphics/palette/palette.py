from src.ndstools.formats.file import File

from typing import List


class PaletteColor:
    """
    A RGB color of a palette.
    """

    r: int
    g: int
    b: int

    def __init__(self, r: int, g: int, b: int):
        self.r = r
        self.g = g
        self.b = b

    @classmethod
    def from_bytes(cls, data: bytes):
        if len(data) != 2:
            raise Exception("Need exactly 2 bytes to create a color.")
        value = int.from_bytes(data, "little")
        r = value & 0b11111
        g = (value >> 5) & 0b11111
        b = (value >> 10) & 0b11111

        red = round(r * 255 / 31)
        green = round(g * 255 / 31)
        blue = round(b * 255 / 31)

        return cls(red, green, blue)

    @classmethod
    def from_list(cls, L: List[int]):
        return cls(L[0], L[1], L[2])

    def to_bytes(self):
        r = round(self.r * 31 / 255)
        g = round(self.g * 31 / 255)
        b = round(self.b * 31 / 255)
        data = r + (g << 5) + (b << 10)
        return data.to_bytes(2, "little")

    def to_int_list(self) -> List[int]:
        return [self.r, self.g, self.b]


class Palette(File):
    """
    The Parent Class for palette files.
    """

    color_count: int
    colors: List[PaletteColor]

    def get_colors(self) -> List[PaletteColor]:
        """
        Returns the palette colors.

        :returns: A list of PaletteColor.
        """
        raise Exception("Not implemented")

    def set_colors(self, colors: List[PaletteColor]):
        """
        Set the palette colors.

        :param colors: A list of PaletteColor.

            WARNING: it's important to note that Nintendo DS palette colors are stored in 5 bits per
            component, meaning that imported colors might be slightly different than expected.

            For example, R = 4 would be approximated to R = 0, and R = 5 would be approximated to R = 8.

        """
        pass

    def set_colors_with_im_list(self, colors: List[int]):
        pass

    def get_bit_depth(self) -> int | None:
        """
        Returns the bit depth of the file (if it's defined).

        :returns: An int, the bit depth.
        """
        pass

    def set_bit_depth(self, bit_depth: int):
        """
        Set the bit depth of the file (if it's defined).

        :param bit_depth: An int, the bit depth.
        """
        pass
