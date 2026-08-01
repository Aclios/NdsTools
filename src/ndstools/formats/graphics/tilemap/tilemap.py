from src.ndstools.formats.file import File
from src.ndstools.fs import EndianBinaryReader, EndianBinaryWriter
from src.ndstools.formats.graphics.core import Tile
from PIL import Image


class MapData:
    """
    The MapData object contains the info of a tile of a mapped image: tile index, palette index, and rotation flags.
    """

    def __init__(
        self,
        tile_idx: int,
        pal_idx: int,
        flip_top_bottom: bool = False,
        flip_left_right: bool = False,
    ):
        self.tile_idx = tile_idx
        self.pal_idx = pal_idx
        self.flip_top_bottom = flip_top_bottom
        self.flip_left_right = flip_left_right

    @classmethod
    def read(cls, f: EndianBinaryReader):
        flip_top_bottom = False
        flip_left_right = False
        data = f.read_UInt16()
        pal_idx = data // 0x1000
        data -= pal_idx * 0x1000
        if data >= 0x800:
            data -= 0x800
            flip_top_bottom = True
        if data >= 0x400:
            data -= 0x400
            flip_left_right = True
        tile_idx = data
        return cls(tile_idx, pal_idx, flip_top_bottom, flip_left_right)

    def write_to(self, f: EndianBinaryWriter) -> None:
        """
        Writes the MapInfo data to the stream f.
        """
        data = self.pal_idx * 0x1000
        if self.flip_top_bottom:
            data += 0x800
        if self.flip_left_right:
            data += 0x400
        data += self.tile_idx
        f.write_UInt16(data)

    def get_tile_im(self, tiles: list[Tile]):
        """
        Returns a PIL Image representing the tile defined by this.

        :param tiles: A list of Tiles, generated from the Bitmap file associated to the Tilemap file.

        :returns: A 8x8 PIL Image representing the tile.
        """
        tile_im = tiles[self.tile_idx].to_im(self.pal_idx)
        if self.flip_top_bottom:
            tile_im = tile_im.transpose(Image.FLIP_TOP_BOTTOM)
        if self.flip_left_right:
            tile_im = tile_im.transpose(Image.FLIP_LEFT_RIGHT)
        return tile_im


class Tilemap(File):
    """
    The Parent Class for tilemap files.
    """

    def get_mapdata(self) -> list[MapData]:
        """
        Returns tile mapping data.

        :returns: A list of MapData objects.
        """
        raise Exception("Not implemented")

    def set_mapdata(self, mapdata: list[MapData]):
        """
        Set tile mapping data.

        :params mapdata: A list of MapData objects.
        """
        pass

    def get_im_size(self) -> tuple[int, int] | None:
        """
        Returns the image size of the file (if it's defined).

        :returns: A tuple (width, height).
        """
        pass

    def set_im_size(self, im_size: tuple[int, int]):
        """
        Set the image size of the file (if it's defined).

        :param im_size: A tuple (width, height).
        """
        pass
