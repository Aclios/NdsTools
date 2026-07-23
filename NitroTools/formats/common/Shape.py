from PIL import Image
from .Tile import Tile
from ..common import eightbpp_to_fourbpp


class Shape:
    def __init__(
        self,
        in_data: list[Tile] | Image.Image,
        size: tuple[int, int],
        pal_idx: int,
        bit_depth: int,
        linear: bool,
    ):

        assert size in valid_shape_size, "Invalid shape size"
        self.bit_depth = bit_depth
        self.size = size
        self.width, self.height = size
        self.tile_width_count = self.width // 8
        self.tile_height_count = self.height // 8
        self.tile_count = self.tile_width_count * self.tile_height_count
        self.pal_idx = pal_idx
        self.linear = linear

        if isinstance(in_data, list):
            self.tiles = in_data
            self.image = self.build_image()

        elif isinstance(in_data, Image.Image):
            self.tiles = []
            for j in range(self.tile_height_count):
                for i in range(self.tile_width_count):
                    tile = Tile(in_data.crop((i * 8, j * 8, (i + 1) * 8, (j + 1) * 8)))
                    self.tiles.append(tile)
            self.image = in_data

    def build_image(self) -> Image.Image:
        it_tiles = iter(self.tiles)
        image = Image.new(mode="P", size=self.size)
        if self.linear:
            data = b""
            for j in range(self.tile_height_count):
                for i in range(self.tile_width_count):
                    tile = next(it_tiles)
                    data += tile.to_bytes(self.pal_idx)
            image.putdata(data=data)

        else:
            for j in range(self.tile_height_count):
                for i in range(self.tile_width_count):
                    tile = next(it_tiles)
                    image.paste(tile.to_im(self.pal_idx), (i * 8, j * 8))

        return image

    def to_bytes(self) -> bytes:
        if self.linear:
            data = self.image.tobytes()
            if self.bit_depth == 4:
                data = eightbpp_to_fourbpp(data)

        else:
            data = bytearray()
            for tile in self.tiles:
                data += tile.to_bytes()

        return data

    def get_tiles(self):
        return self.tiles


valid_shape_size = [
    (8, 8),
    (16, 16),
    (32, 32),
    (64, 64),
    (16, 8),
    (32, 8),
    (32, 16),
    (64, 32),
    (8, 16),
    (8, 32),
    (16, 32),
    (32, 64),
]
