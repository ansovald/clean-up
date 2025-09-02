import random
import json
from string import Template
from typing import Dict, Tuple

EMPTY_SYMB = "◌"
INITIAL_DISTANCE = "Initial Distance"
TOTAL_DISTANCE = "Total Distance"
DISTANCE_SCORE = "Distance Score"
DISTANCE_REDUCTION_SCORE = "Distance Reduction Score"
EXPECTED_DISTANCE_SCORE = "Expected Distance Score"

def number_to_letter(number: int) -> str:
        """
        Converts a number to a letter (1 -> A, 2 -> B, ..., 26 -> Z).
        :param number: The number to convert
        :return: The corresponding letter
        """
        if 1 <= number <= 26:
            return chr(number + 64)
        raise ValueError(f"Number {number} is out of bounds for letter conversion (1-26)")

def letter_to_number(letter: str) -> int:
        """
        Converts a letter to a number (A -> 1, B -> 2, ..., Z -> 26).
        :param letter: The letter to convert
        :return: The corresponding number
        """
        if len(letter) == 1 and letter.isalpha():
            return ord(letter.upper()) - 64
        raise ValueError(f"Letter '{letter}' is not a valid single letter (A-Z)")

class GameGrid:
    def __init__(self, grid: str=None, move_messages: dict=None, object_string: str=None, show_coords: bool = False):
        """
        Initializes the GameGrid class
        """
        self.grid = self.parse_grid(grid) if grid else []
        self.width = len(self.grid[0]) if self.grid else 0
        self.height = len(self.grid) if self.grid else 0
        self.objects: Dict[str, Tuple[int, int]] = {}
        if object_string:
            self.place_objects(list(object_string))
        self.move_messages = move_messages
        self.show_coords = show_coords

    def get_dimensions(self) -> tuple[int, int]:
        """
        Returns the dimensions of the grid.
        :return: A tuple (width, height)
        """
        return self.width, self.height
            
    def parse_grid(self, grid: str) -> list[list[str]]:
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

    @classmethod
    def from_json(cls, file: str='resources/grids/gs12x8_b2.json', index: int=None):
        """
        Initializes a grid from a json file
        """
        with open(file, 'r') as f:
            all_grids = json.load(f)
        if index is None:
            index = random.randint(0, len(all_grids) - 1)
        return cls(all_grids[str(index)])
    
    @classmethod
    def pair_from_json(cls, file: str='resources/grids/gs12x8_b2.json', index: int=None):
        """
        Initializes two grids from a json file
        """
        with open(file, 'r') as f:
            all_grids = json.load(f)
        if index is None:
            index = random.randint(0, len(all_grids) - 1)
        model1 = all_grids[str(index)]
        model2 = all_grids[str(index)]
        return cls(model1), cls(model2)
    
    def __str__(self, empty = False, show_coords: bool = None):
        """
        Returns a string representation of the grid.
        :param empty: If True, returns the empty grid without objects
        :param coords: If True, includes coordinates in the string representation
        :return: A string representation of the grid
        """
        if not show_coords:
            coords = self.show_coords
        else:
            coords = show_coords
        i = -1
        if empty:
            i = 0
        grid_str = ""
        if coords:
            grid_str += " " + "".join([number_to_letter(i) for i in range(1,self.width-1)]) + "\n"
        for j, row in enumerate(self.grid):
            grid_str += "".join([cell[i] for cell in row])
            if coords:
                if not (j == 0 or j == len(self.grid) - 1):
                    grid_str += f" {j}"
            grid_str += "\n"
        return grid_str
    
    def place_objects(self, objects: list[str] | str):
        """
        Places objects on the grid.
        :param objects: List of objects to place on the grid
        """
        for obj in objects: 
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            while self.grid[y][x][-1] != EMPTY_SYMB:
                x = random.randint(0, self.width - 1)
                y = random.randint(0, self.height - 1)
            self.grid[y][x].append(obj)
            if obj not in self.objects:
                self.objects[obj] = None
            self.objects[obj] = (x, y)

    def get_objects(self):
        """
        Returns a dict of objects and their positions on the grid.
        """
        return {obj: self.objects[obj] for obj in self.objects if self.objects[obj] is not None}
    
    def object_set(self):
        """
        Returns a set of all objects in the grid.
        """
        return set(self.objects.keys())
    
    def object_string(self):
        """
        Returns a string representation of all objects in the grid.
        """
        return "'" + "', '".join(self.objects.keys()) + "'"
    
    def object_list(self):
        """
        Returns a list of all objects in the format used by instancegenerator: [{'id': 'A', 'coord': [x, y]}, ...]
        """
        return [{'id': obj, 'coord': [pos[0], pos[1]]} for obj, pos in self.objects.items() if pos is not None]

    def set_objects(self, objects: list[dict]):
        """
        Sets the positions of objects on the grid, as loaded from an instance json file.
        :param objects: A list of dictionaries of type {'id': 'A', 'coord': [x, y]}
        """
        for object in objects:
            obj = object['id']
            x, y = object['coord']
            x = int(x)
            y = int(y)
            if 0 <= x < self.width and 0 <= y < self.height:
                if self.grid[y][x][-1] != EMPTY_SYMB:
                    raise ValueError(f"Position ({x}, {y}) is not empty for object '{obj}'")
                self.grid[y][x].append(obj)
                self.objects[obj] = (x, y)
            else:
                raise ValueError(f"Position ({x}, {y}) is out of bounds for object '{obj}'")
    
    def move_abs(self, obj, x, y, check_empty=True):
        """
        Moves an object to a specific position on the grid.
        :param obj: The object to move
        :param x: The x-coordinate to move to (0-9+)
        :param y: The y-coordinate to move to (A-Z)
        Returns:
            A tuple (success, message) where success is a boolean indicating if the move was successful,
            and message is a string with the result of the move.
        """
        x_letter = x
        if isinstance(x, str):
            try:
                x = letter_to_number(x)
            except ValueError:
                raise ValueError(f"Invalid x-coordinate: {x}. It should be a capital letter.")
        if isinstance(y, str):
            try:
                y = int(y)
            except ValueError:
                raise ValueError(f"Invalid y-coordinate: {y}. It should be an string that can be converted to an integer.")
        if obj in self.objects:
            old_x, old_y = self.objects[obj]
            if not (0 <= x < self.width and 0 <= y < self.height):
                return False, Template(self.move_messages["out_of_bounds"]).substitute(x=x_letter, y=y)
            if check_empty and self.grid[y][x][-1] != EMPTY_SYMB:
                return False, Template(self.move_messages["not_empty"]).substitute(object=self.grid[y][x][-1], x=x_letter, y=y)
            self.grid[old_y][old_x] = self.grid[old_y][old_x][:-1]  # Remove the object from the old position
            self.grid[y][x].append(obj)  # Place the object at the new position
            self.objects[obj] = (x, y)
            
            return True, Template(self.move_messages["successful"]).substitute(object=obj, x=x_letter, y=y, grid=str(self))
        else:
            return False, Template(self.move_messages["obj_not_found"]).substitute(object=obj)

    def get_position(self, obj: str):
        """
        Returns the position of the object on the grid.
        :param obj: The object to find
        :return: A tuple (x, y) representing the position of the object
        """
        if obj in self.objects:
            return self.objects[obj]
        raise ValueError(f"Object '{obj}' not found in the grid")
        
    def distance_sum(self, other):
        """
        Compares two grids and returns the sum of Euclidean distances between the identical objects
        """
        if not isinstance(other, GameGrid):
            raise ValueError("Comparison is only supported between two GameGrid instances")
        if not self.object_set() == other.object_set():
            raise ValueError("Grids must have the same objects for comparison")
        
        total_distance = 0.0
        all_distances = {}
        for obj in self.objects:
            if obj in other.objects:
                x1, y1 = self.get_position(obj)
                x2, y2 = other.get_position(obj)
                distance = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
                all_distances[obj] = distance
                total_distance += distance
        return total_distance
    
    def expected_total_distance(self):
        """
        Returns the expected total distance for a given number of objects.
        The formula is based on the average distance between objects in a grid.
        """
        avg_x_dist = (self.width ** 2 - 1) / (3 * self.width)
        avg_y_dist = (self.height ** 2 - 1) / (3 * self.height)
        avg_dist = (avg_x_dist ** 2 + avg_y_dist ** 2) ** 0.5
        return avg_dist * self.object_set().__len__()
    
    # ----------------------
    # Note: (sub)metric computations are centralized in the MetricCalculator class.
    # see `resources/utils/metrics.py`
    # ----------------------
    # def expected_distance_score(self, distance_sum: float):
    #     """
    #     Returns the expected distance score based on the distance sum and the expected total distance.
    #     """
    #     expected_distance = self.expected_total_distance()
    #     if expected_distance <= 0:
    #         raise ValueError("Expected distance must be a positive number")
    #     return max(0, 1 - (distance_sum / expected_distance))
    
    # def distance_reduction_score(self, distance_sum: float, initial_distance: float):
    #     """
    #     Returns the distance reduction score based on the distance sum and the initial distance.
    #     """
    #     if initial_distance is None or initial_distance <= 0:
    #         raise ValueError("Initial distance must be a positive number")
    #     return max(0, 1 - (distance_sum / initial_distance))

    # def get_scores(self, other, initial_distance: float = None):
    #     """
    #     Returns a dictionary with the distance sum and distance score compared to the worst case scenario.
    #     """
    #     if not isinstance(other, GameGrid):
    #         raise ValueError("Comparison is only supported between two GameGrid instances")
    #     if not self.object_set() == other.object_set():
    #         raise ValueError("Grids must have the same objects for comparison")
    #     if not initial_distance:
    #         raise ValueError("Initial distance must be provided for score calculation")
        
    #     distance_sum = self.distance_sum(other)

    #     expected_distance_score = self.expected_distance_score(distance_sum)
    #     distance_reduction_score = self.distance_reduction_score(distance_sum, initial_distance)

    #     distance_score = (expected_distance_score + distance_reduction_score) / 2
        
    #     return {
    #         TOTAL_DISTANCE: distance_sum,
    #         EXPECTED_DISTANCE_SCORE: expected_distance_score,
    #         DISTANCE_REDUCTION_SCORE: distance_reduction_score,
    #         DISTANCE_SCORE: distance_score
    #     }
