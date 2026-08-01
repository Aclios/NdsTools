from .utils import (
    empty_im,
    paste_alpha,
    get_image_colors,
)
from src.ndstools.formats.graphics.core.oam import OAM, Tile
from src.ndstools.formats.graphics.core.utils import (
    convert_from_eightbpp,
    convert_to_eightbpp,
    get_expected_tile_count,
)


from .bitmap import *
from .palette import *
from .tilemap import *
from .cell import *
from PIL import Image


class ImageCanva:
    _images: list[Image.Image]

    def __init__(
        self,
        bitmap: Bitmap = None,
        palette: Palette = None,
        tilemap: Tilemap = None,
        cell: NCER = None,
        bit_depth: int = None,
        im_size: tuple[int, int] = None,
        oam_size: tuple[int, int] = (8, 8),
        transparency: bool = False,
        linear: bool = False,
    ):

        self.load_bitmap(bitmap)
        self.load_palette(palette)
        self.load_cell(cell)
        self.load_tilemap(tilemap)

        self.set_im_size(im_size)
        self.set_oam_size(oam_size)
        self.set_bit_depth(bit_depth)
        self.set_transparency(transparency)
        self.set_linear(linear)

    def load_bitmap(self, bitmap: Bitmap):
        """
        Load a Bitmap object to the Canva, and set its parameters (bit depth, image size, linearity) if they exist.

        :params Bitmap: A Bitmap object.
        """
        self.bitmap = bitmap
        if bitmap is not None:
            self.set_bit_depth(self.bitmap.get_bit_depth())
            self.set_im_size(self.bitmap.get_im_size())
            self.set_linear(self.bitmap.get_linear_flag())

    def load_tilemap(self, tilemap: Tilemap):
        """
        Load a Tilemap object to the Canva, and set its parameters (image size) if they exist.

        :params Tilemap: A Tilemap object.
        """
        self.tilemap = tilemap
        if tilemap is not None:
            self.set_im_size(self.tilemap.get_im_size())

    def load_palette(self, palette: Palette):
        """
        Load a Palette object to the Canva, and set its parameters (bit depth) if they exist.

        :params Palette: A Palette object.
        """
        self.palette = palette
        if palette is not None:
            self.set_bit_depth(self.palette.get_bit_depth())

    def load_cell(self, cell: NCER):
        """
        Load a Cell object to the Canva.

        :params Cell: A NCER object.
        """
        self.cell = cell

    def set_im_size(self, im_size: tuple[int, int]):
        """
        Set the image size of the Canva.

        This is only relevant if you are dealing with raw Bitmap/Palette.

        :params im_size: A tuple (width, height).
        """
        if im_size is not None:
            self.im_size = im_size
            self.im_width, self.im_height = im_size

    def set_oam_size(self, oam_size: tuple[int, int]):
        """
        Set the OAM size of the Canva.

        This is only relevant if you are dealing with raw Bitmap/Palette.

        :params im_size: A tuple (OAM_width, OAM_height).
        """
        if oam_size is not None:
            self.oam_size = oam_size
            self.oam_width, self.oam_height = oam_size

    def set_bit_depth(self, bit_depth: int):
        """
        Set the bit depth of the Canva.

        This is only relevant if you are dealing with raw Bitmap/Palette.

        :params bit_depth: The bit depth.
        """
        if bit_depth in [2, 4, 8]:

            self.bit_depth = bit_depth

        elif bit_depth is None:
            pass

        else:
            raise Exception("Invalid bit depth value. Should be either 2, 4 or 8.")

    def set_linear(self, linear_flag: bool):
        """
        Set the linearity of the Canva. If it's set to False, the Bitmap data will be read as tiles. If it's set to True,
        the Bitmap data will be read left/right top/bottom.

        This is only relevant if you are dealing with raw Bitmap/Palette.

        :params linear_flag: The linear flag.
        """
        if linear_flag is not None:
            self.linear = linear_flag

    def set_transparency(self, transparency: bool):
        """
        Set whether the index 0 of the palette indicates fully transparent pixels.

        This isn't required, since transparent pixels usually have a distinct color.

        :params transparency: Transparency flag.
        """
        if transparency is not None:
            self.transparency = transparency

    def generate_tile_list(self):
        """
        Generate tiles from the loaded Bitmap.
        """
        tile_datasize = self.bit_depth * 8
        data = self.bitmap.get_data()
        tile_count = len(data) // tile_datasize
        tiles = [
            Tile(data[tile_datasize * idx : tile_datasize * (idx + 1)], self.bit_depth)
            for idx in range(tile_count)
        ]
        return tiles

    def _build_hor_image(self, pal_idx: int = 0):
        """
        Build a tiled image, by solely using a Bitmap and a Palette.

        :params pal_idx: The index of the subpalette the image should follow. It is useful if the same Bitmap has several colorings,
        for example for an animation.
        """
        oam_width_count = self.im_width // self.oam_width
        oam_height_count = self.im_height // self.oam_height
        im = empty_im(
            self.im_size, self.palette.get_colors(), self.bit_depth, self.transparency
        )
        tile_idx = 0
        tiles = self.generate_tile_list()
        tile_count_per_oam = (self.oam_width // 8) * (self.oam_height // 8)
        for j in range(oam_height_count):
            for i in range(oam_width_count):
                oam = OAM(
                    tiles[tile_idx : tile_idx + tile_count_per_oam],
                    self.oam_size,
                    pal_idx,
                    self.bit_depth,
                    False,
                )
                tile_idx += tile_count_per_oam
                im.paste(oam.image, (i * self.oam_width, j * self.oam_height))
        return [im]

    def _build_linear_image(self, pal_idx: int):
        """
        Build a linear image, by solely using a Bitmap and a Palette.

        :params pal_idx: The index of the subpalette the image should follow. It is useful if the same Bitmap has several colorings,
        for example for an animation.
        """
        im = empty_im(
            self.im_size, self.palette.get_colors(), self.bit_depth, self.transparency
        )
        eightbpp_data = convert_to_eightbpp(
            self.bitmap.get_data(), self.bit_depth, pal_idx
        )
        im.putdata(eightbpp_data[: self.im_width * self.im_height])
        return [im]

    def _build_image_with_tilemap(self):
        """
        Build an image, by using a Bitmap, a Palette, and a Tilemap.
        """
        im = empty_im(
            self.im_size, self.palette.get_colors(), self.bit_depth, self.transparency
        )
        tiles = self.generate_tile_list()
        maps = iter(self.tilemap.get_mapdata())
        for j in range(im.height // 8):
            for i in range(im.width // 8):
                map = next(maps)
                tile_im = map.get_tile_im(tiles)
                im.paste(tile_im, (i * 8, j * 8))
        return [im]

    def _build_cells(self):
        """
        Build the different frames defined by a Cell, using a Bitmap and a Palette.
        """
        tiles = self.generate_tile_list()
        cell_images = []
        for cell_bank in self.cell.cebk.cells:
            if len(cell_bank.oam_data_list) == 0:
                cell_images.append(None)
                continue

            min_x = min([oam_data.x_pos for oam_data in cell_bank.oam_data_list])
            min_y = min([oam_data.y_pos for oam_data in cell_bank.oam_data_list])
            max_x = max(
                [
                    oam_data.x_pos + oam_data.size[0]
                    for oam_data in cell_bank.oam_data_list
                ]
            )
            max_y = max(
                [
                    oam_data.y_pos + oam_data.size[1]
                    for oam_data in cell_bank.oam_data_list
                ]
            )
            cell_im_size = (max_x - min_x, max_y - min_y)
            cell_im = empty_im(
                cell_im_size, self.palette.get_colors(), self.bit_depth, True
            )

            if self.bit_depth == 4:
                transparency_idx = [i * 16 for i in range(16)]
            else:
                transparency_idx = [0]

            for oam_data in cell_bank.oam_data_list[::-1]:
                if self.bit_depth == 4:
                    tile_offset = oam_data.tile_index * self.cell.cebk.tile_index_offset
                else:
                    tile_offset = (
                        oam_data.tile_index * self.cell.cebk.tile_index_offset // 2
                    )

                oam = OAM(
                    tiles[
                        tile_offset : tile_offset
                        + get_expected_tile_count(oam_data.size)
                    ],
                    oam_data.size,
                    oam_data.pal_idx,
                    self.bit_depth,
                    self.linear,
                )
                oam_im = oam.image
                if oam_data.ver_flip:
                    oam_im = oam_im.transpose(Image.FLIP_TOP_BOTTOM)
                if oam_data.hor_flip:
                    oam_im = oam_im.transpose(Image.FLIP_LEFT_RIGHT)

                cell_im = paste_alpha(
                    cell_im,
                    oam_im,
                    (oam_data.x_pos - min_x, oam_data.y_pos - min_y),
                    transparency_idx,
                )
            cell_images.append(cell_im)

        return cell_images

    def resolve(self, pal_idx: int = 0):
        """
        Build automatically the image(s) using the objects currently loaded in the Canva.
        You can later get them with the .images property.

        :params pal_idx: The index of the subpalette the image should follow. It is useful if the same Bitmap has several colorings,
        for example for an animation. It isn't used if there is a Tilemap or a Cell object.
        """
        assert (
            self.bitmap is not None and self.palette is not None
        ), "At least a palette and a bitmap are required"
        if self.cell is not None:
            self._images = self._build_cells()
        elif self.tilemap is not None:
            self._images = self._build_image_with_tilemap()
        else:
            if not self.linear:
                self._images = self._build_hor_image(pal_idx)
            else:
                self._images = self._build_linear_image(pal_idx)

    def import_image(self, im_filepath: str, cell_idx: int = 0):
        im = Image.open(im_filepath)
        assert (
            im.mode == "P"
        ), "Invalid png type, pyNitro is expecting a color indexed png."
        assert (
            self.bitmap is not None and self.palette is not None
        ), "At least a palette and a bitmap are required"
        if self.cell is not None:
            self._import_cell(im, cell_idx)
        elif self.tilemap is not None:
            self._import_image_with_tilemap(im)
        else:
            if not self.linear:
                self._import_hor_image(im)
            else:
                self._import_linear_image(im)

    def _import_cell(self, im: Image.Image, cell_idx: int):
        """
        Import an image to a cell.

        :params im: The Image.
        :params cell_idx: The cell index.
        """
        self.tiles = self.generate_tile_list()
        cell = self.cell.cebk.cells[cell_idx]
        min_x = min([oam_data.x_pos for oam_data in cell.oam_data_list])
        min_y = min([oam_data.y_pos for oam_data in cell.oam_data_list])

        for oam_data in cell.oam_data_list:
            oam = OAM(
                im.crop(
                    (
                        oam_data.x_pos - min_x,
                        oam_data.y_pos - min_y,
                        oam_data.x_pos + oam_data.oam.width - min_x,
                        oam_data.y_pos + oam_data.oam.height - min_y,
                    )
                ),
                oam_data.size,
                oam_data.pal_idx,
                self.bit_depth,
                self.linear,
            )
            new_tiles = oam.get_tiles()

            if self.bit_depth == 4:
                tile_offset = oam_data.tile_index * self.cell.cebk.tile_index_offset
            else:
                tile_offset = (
                    oam_data.tile_index * self.cell.cebk.tile_index_offset // 2
                )

            self.tiles[tile_offset : tile_offset + oam.tile_count] = new_tiles

        newdata = bytearray()
        for tile in self.tiles:
            newdata += tile.to_bytes()

        self.bitmap.set_data(newdata)
        self.palette.set_colors(get_image_colors(im))

    def _import_image_with_tilemap(self, im: Image.Image):
        """
        Import an image that use a tilemap.

        :params im: The Image.
        """
        mapinfos: list[MapData] = []
        data = bytes()
        tiles_data: list[bytes] = []
        for j in range(im.height // 8):
            for i in range(im.width // 8):
                tile_data = im.crop((i * 8, j * 8, (i + 1) * 8, (j + 1) * 8)).tobytes()
                if self.bit_depth == 8:
                    pal_idx = 0
                elif self.bit_depth == 4:
                    pal_idx = tile_data[0] // 0x10
                elif self.bit_depth == 2:
                    pal_idx = tile_data[0] // 0x4
                tile_data = convert_from_eightbpp(tile_data, self.bit_depth)
                if tile_data in tiles_data:
                    tile_idx = tiles_data.index(tile_data)
                else:
                    tiles_data.append(tile_data)
                    data += tile_data
                    tile_idx = len(tiles_data) - 1
                mapinfos.append(MapData(tile_idx, pal_idx))

        self.bitmap.set_data(data)
        self.palette.set_colors(get_image_colors(im))
        self.tilemap.set_mapdata(mapinfos)
        self.tilemap.set_im_size(im.size)

    def _import_hor_image(self, im: Image.Image):
        """
        Import an tiled image that only use a bitmap and a palette.

        :params im: The Image.
        """
        data = bytearray()
        for j in range(im.height // self.oam_height):
            for i in range(im.width // self.oam_width):
                oam = OAM(
                    im.crop(
                        (
                            i * self.oam_width,
                            j * self.oam_height,
                            (i + 1) * self.oam_width,
                            (j + 1) * self.oam_height,
                        )
                    ),
                    self.oam_size,
                    0,
                    self.bit_depth,
                    False,
                )
                data += oam.to_bytes()
        self.bitmap.set_data(data)
        self.bitmap.set_im_size(im.size)
        self.palette.set_colors(get_image_colors(im))

    def _import_linear_image(self, im: Image.Image):
        """
        Import an linear image that only use a bitmap and a palette.

        :params im: The Image.
        """
        data = convert_from_eightbpp(im.tobytes(), self.bit_depth)
        self.bitmap.set_data(data)
        self.bitmap.set_im_size(im.size)
        self.palette.set_colors(get_image_colors(im))

    @property
    def image(self):
        if not self._images:
            raise Exception("No images found. Did you call .resolve() before?")
        return self._images[0]

    @property
    def images(self):
        if not self._images:
            raise Exception("No images found. Did you call .resolve() before?")
        return self._images
