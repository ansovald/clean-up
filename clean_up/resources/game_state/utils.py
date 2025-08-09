from typing import List, Tuple, TypedDict
import base64
import math
import random
from PIL import Image

EMPTY_SYMBOL = "◌"
ICON_SIZE = 128 # Icons are square

class GameObject(TypedDict):
    id: str
    coord: Tuple[int, int]

class Icon(GameObject):
    freepik_id: str  # Unique identifier for the icon
    url: str = None  # URL to the icon image
    img: str = None  # Base64 encoded image string

def png_to_base64(png_path):
    """
    Convert a PNG image to a base64 encoded string.
    """
    with open(png_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:image/png;base64,{encoded_string}"

def number_to_letter(number: int) -> str:
    """
    Converts a number to a lowercase letter (1 -> a, 2 -> b, ..., 26 -> z).
    :param number: The number to convert
    :return: The corresponding lowercase letter
    """
    if 1 <= number <= 26:
        return chr(number + 96)
    raise ValueError(f"Number {number} is out of bounds for lowercase letter conversion (1-26)")

def letter_to_number(letter: str) -> int:
    """
    Converts a lowercase letter to a number (a -> 1, b -> 2, ..., z -> 26).
    :param letter: The lowercase letter to convert
    :return: The corresponding number
    """
    if len(letter) == 1 and letter.isalpha():
        return ord(letter.lower()) - 96
    raise ValueError(f"Letter '{letter}' is not a valid single lowercase letter (a-z)")

def place_objects(modality: str, objects: List[GameObject], background: str) -> List[GameObject]:
    """
    Place objects on the grid based on the modality.
    :param modality: The modality of the game (e.g., 'text', 'image')
    :param objects: List of GameObject to place
    :param grid: The grid string representation
    :return: List of GameObject with updated coordinates
    """
    if modality == 'text':
        return place_grid_objects(objects, background)
    elif modality == 'image':
        # Load the background image to get dimensions
        dim = Image.open(background).size
        return place_icons(objects, dim)
    else:
        raise ValueError(f"Unsupported modality: {modality}")

def place_grid_objects(objects: List[GameObject], grid: str) -> List[GameObject]:
    """
    Sample unique coordinates for each object in objects.
    :param grid: The grid string representation
    :param width: The width of the grid
    :param objects: List of GameObject to place
    :return: List of GameObject with updated coordinates
    """
    width = grid.index('\n') + 1 if '\n' in grid else len(grid)
    # + 1 to account for the newline character
    empty_indices = [i for i, char in enumerate(grid) if char == EMPTY_SYMBOL]
    random.shuffle(empty_indices)
    if len(empty_indices) < len(objects):
        raise ValueError("Not enough empty positions in the grid to place all objects.")
    for obj in objects:
        # For some reason, sample() produces conspicuously many duplicate indices when called twice
        # random.choice() works better
        index = random.choice(empty_indices)
        empty_indices.remove(index)  # Ensure unique placement
        x = index % width
        y = index // width
        obj['coord'] = (x, y)
    return objects

def place_icons(objects: List[Icon], img_size: Tuple[int, int]) -> List[Icon]:
    """
    Place icons on the background image and assign them randomized IDs.
    :param objects: List of Icon objects to place
    :param img_size: Size of the icons (width, height)
    :return: List of placed Icon objects with updated coordinates
    """
    width, height = img_size
    step = (ICON_SIZE // 50) * 50  # the largest multiple of 50 that is less than or equal to w
    min_x = math.ceil(ICON_SIZE / 2 / step) * step
    max_x = (width - ICON_SIZE // 2) // step * step
    min_y = math.ceil(ICON_SIZE / 2 / step) * step
    max_y = (height - ICON_SIZE // 2) // step * step

    valid_positions = [
        (x, y)
        for x in range(min_x, max_x + 1, step)
        for y in range(min_y, max_y + 1, step)
    ]
    random.shuffle(valid_positions)
    assert len(valid_positions) >= len(objects), "Not enough valid positions to place all objects."
    coords = random.sample(valid_positions, len(objects))
    random.shuffle(objects)
    # Assign IDs and random unique coordinates
    for i, obj in enumerate(objects):
        obj['id'] = chr(ord('A') + i)
        obj['coord'] = coords[i]
    return objects

def parse_grid(grid: str) -> list[list[str]]:
    """
    Parses the grid from a string into a 2D list.
    """
    grid = grid.strip().split("\n")
    parsed_grid = []
    for row in grid:
        parsed_row = []
        for char in row:
            parsed_row.append([char])
        parsed_grid.append(parsed_row)
    return parsed_grid