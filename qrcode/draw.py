from functools import partial
from typing import Dict, List, Callable, Literal, TypeAlias, Tuple

import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageDraw

from qrcode.utils import convert_to_version, convert_to_grid_size
from qrcode.encode import encode

CoordinateValueMap: TypeAlias = Dict[Tuple[int, int], int]
ErrorCorrectionLevels = Literal["L", "M", "Q", "H"]

WHITE = 0
BLACK = 1
DUMMY_VALUE = -2


def get_empty_grid(size: int = 21):
    grid = np.zeros((size, size))
    return grid


def get_timing_pattern(grid_size: int = 21) -> CoordinateValueMap:
    fixed_row, fixed_col = 6, 6
    timing_pattern_row_black = {(fixed_row, x): BLACK for x in range(0, grid_size, 2)}
    timing_pattern_row_white = {(fixed_row, x): WHITE for x in range(1, grid_size, 2)}
    timing_pattern_col_black = {(x, fixed_col): BLACK for x in range(0, grid_size, 2)}
    timing_pattern_col_white = {(x, fixed_col): WHITE for x in range(1, grid_size, 2)}
    result: CoordinateValueMap = {
        **timing_pattern_row_black,
        **timing_pattern_row_white,
        **timing_pattern_col_black,
        **timing_pattern_col_white,
    }
    return result


def create_row(fixed_row_index, col_start, col_end, value):
    return {(fixed_row_index, col): value for col in range(col_start, col_end)}


def create_col(fixed_col_index, row_start, row_end, value):
    return {(row, fixed_col_index): value for row in range(row_start, row_end)}


def finder_pattern_generator(row, col, grid_size) -> CoordinateValueMap:
    result = {}
    for r in range(-1, 8):
        if row + r <= -1 or grid_size <= row + r:
            continue

        for c in range(-1, 8):
            if col + c <= -1 or grid_size <= col + c:
                continue

            if (0 <= r <= 6 and c in {0, 6}) or (0 <= c <= 6 and r in {0, 6}) or (2 <= r <= 4 and 2 <= c <= 4):
                result[(row + r, col + c)] = BLACK
            else:
                result[(row + r, col + c)] = WHITE
    return result


def get_finder_patterns(
    finder_pattern_generator: Callable[[int, int, int], CoordinateValueMap], grid_size
) -> CoordinateValueMap:
    top_left = finder_pattern_generator(0, 0, grid_size)
    bottom_left = finder_pattern_generator(grid_size - 7, 0, grid_size)
    top_right = finder_pattern_generator(0, grid_size - 7, grid_size)
    return {**top_left, **bottom_left, **top_right}


def get_seperator_pattern(grid_size) -> CoordinateValueMap:
    length = 8
    length_index = length - 1

    create_white_row = partial(create_row, value=WHITE)
    create_white_col = partial(create_col, value=WHITE)

    top_left_row = create_white_row(fixed_row_index=length_index, col_start=0, col_end=length)
    top_left_col = create_white_col(fixed_col_index=length_index, row_start=0, row_end=length)

    top_right_row = create_white_row(fixed_row_index=length_index, col_start=grid_size - length, col_end=grid_size)
    top_right_col = create_white_col(fixed_col_index=grid_size - length, row_start=0, row_end=length)

    bottom_right_row = create_white_row(fixed_row_index=grid_size - length, col_start=0, col_end=length)
    bottom_right_col = create_white_col(fixed_col_index=length_index, row_start=grid_size - length, row_end=grid_size)

    result = {**top_left_row, **top_left_col, **top_right_row, **top_right_col, **bottom_right_row, **bottom_right_col}
    return result


def add_quiet_zone(grid):
    horizontal_zone = np.zeros((grid.shape[0], 1))
    grid = np.hstack((grid, horizontal_zone))
    grid = np.hstack((horizontal_zone, grid))

    vertical_zone = np.zeros((1, grid.shape[1]))
    grid = np.vstack((grid, vertical_zone))
    grid = np.vstack((vertical_zone, grid))

    return grid


def override_grid(grid, indexes: Dict[tuple, int]):
    for index, value in indexes.items():
        i, j = index
        grid[i][j] = value
    return grid


def draw_grid_with_pil(grid: np.ndarray, cell_size: int = 20):
    """
    Draw a grid using PIL based on a 2D numpy array.

    Parameters:
    - grid: A 2D numpy array of shape (n, n) containing 0, 1, or -1.
    - cell_size: The size of each cell in the grid in pixels.

    The function will color the cells as follows:
    - 0 will be white
    - 1 will be black
    - -1 will be light gray
    """

    # Validate the shape of the grid
    if grid.shape[0] != grid.shape[1]:
        raise ValueError("The input grid must be square (n x n).")

    # Initialize an image object with white background
    img_size = grid.shape[0] * cell_size
    img = Image.new("RGB", (img_size, img_size), "lightgray")
    draw = ImageDraw.Draw(img)

    color_map = {0: "white", 1: "black", -1: "lightgray", -2: "darkgray"}

    for i in range(grid.shape[0]):  # Rows
        for j in range(grid.shape[1]):  # Columns
            x0, y0 = j * cell_size, i * cell_size  # Corrected here
            x1, y1 = x0 + cell_size, y0 + cell_size
            cell_value = grid[i, j]
            cell_color = color_map.get(cell_value, "white")
            draw.rectangle(((x0, y0), (x1, y1)), fill=cell_color, outline="black")

    img.show()


def iterate_over_grid(grid_size):
    """Iterates over all grid cells in zig-zag pattern and returns an iterator of tuples (row, col)."""
    result = []
    up = True
    for column in range(grid_size - 1, 0, -2):
        if column <= 6:  # skip column 6 because of timing pattern
            column -= 1

        if up:
            row = 20
        else:
            row = 0

        for _ in range(grid_size):
            for col in (column, column - 1):
                result.append((row, col))
            if up:
                row -= 1
            else:
                row += 1
        if up:
            up = False
        else:
            up = True
    return result


def get_data_pattern(binary_str, grid, grid_size):
    # TODO: Implement this function.
    row_col_iter = iterate_over_grid(grid_size)
    for row, col in row_col_iter:
        print(row, col)
        if not binary_str:
            break
        if grid[row][col] == -1:
            grid[row][col] = binary_str[0]
            binary_str = binary_str[1:]
        else:
            continue
    draw_grid_with_pil(grid)


def get_format_information(ecc_level: ErrorCorrectionLevels) -> CoordinateValueMap:
    # TODO: Implement this function.
    """Apply after masking."""
    ecl_binary_indicator_mapping = {"L": "01", "M": "00", "Q": "11", "H": "10"}
    format_information_mask = "101010000010010"
    return {}


def get_dummy_format_information(grid_size) -> CoordinateValueMap:
    result = {}
    for col in range(grid_size):
        if (col <= 7) or (col >= grid_size - 8):
            result[(row := 8, col)] = DUMMY_VALUE

    for row in range(grid_size):
        if row <= 8 or row >= grid_size - 8:
            result[(row, col := 8)] = DUMMY_VALUE

    result[(grid_size - 8, 8)] = BLACK
    return result


def get_version_information(version: int) -> CoordinateValueMap:
    # TODO: Maybe implement this function.
    """Apply after masking."""
    if version <= 6:
        return {}
    else:
        # TODO: TO BE IMPLEMENTED - it should return non-empty dict.
        raise NotImplementedError("Currently only versions below 7 are supported.")


def draw(binary_string: str, version):
    ecc_level = "L"
    grid_size = convert_to_grid_size(version)

    dummy_format_information = get_dummy_format_information(grid_size)
    finder_patterns = get_finder_patterns(finder_pattern_generator, grid_size)
    seperator_pattern = get_seperator_pattern(grid_size)
    timing_pattern = get_timing_pattern(grid_size)

    # format_information = get_format_information(ecc_level)
    # version_information = get_version_information(version)

    grid = np.full((grid_size, grid_size), -1, dtype=int)

    grid = override_grid(grid, dummy_format_information)
    grid = override_grid(grid, timing_pattern)
    grid = override_grid(grid, finder_patterns)
    grid = override_grid(grid, seperator_pattern)
    draw_grid_with_pil(grid)

    data_pattern = get_data_pattern(binary_string, grid, grid_size)

    grid = add_quiet_zone(grid)


if __name__ == "__main__":
    binary_str = encode("hello", ecc_level="LOW")
    draw(binary_str, version=1)
