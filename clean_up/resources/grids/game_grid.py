import random
import json
from string import Template

EMPTY_SYMB = "◌"

move_messages = {}
with open("resources/grids/move_messages.json", "r") as f:
    messages = json.load(f)
    for language in messages:
        move_messages[language] = {}
        for key in messages[language]:
            move_messages[language][key] = Template(messages[language][key])

class GameGrid:
    def __init__(self, grid: str=None, language: str='en', object_string: str=None):
        """
        Initializes the GameGrid class
        """
        self.grid = self.parse_grid(grid) if grid else []
        self.width = len(self.grid[0]) if self.grid else 0
        self.height = len(self.grid) if self.grid else 0
        self.objects = {}
        if object_string:
            self.place_objects(list(object_string))
        self.language = language
        self.show_coords = False  # Default value, can be set later

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
        i = -1
        if empty:
            i = 0
        grid_str = ""
        if coords:
            grid_str += "    " + "".join([str(i % 10) for i in range(1,self.width-1)]) + "\n"
        for j, row in enumerate(self.grid):
            if coords:
                if j == 0 or j == len(self.grid) - 1:
                    grid_str += "   "
                else:
                    grid_str += f"{j} ".rjust(3)
            grid_str += "".join([cell[i] for cell in row]) + "\n"
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
        :param y: The y-coordinate to move to (0-9+)
        """
        if isinstance(x, str):
            try:
                x = int(x) + 1
            except ValueError:
                raise ValueError(f"Invalid x-coordinate: {x}. It should be an integer.")
        if isinstance(y, str):
            try:
                y = int(y) + 1
            except ValueError:
                raise ValueError(f"Invalid x-coordinate: {y}. It should be an integer.")
        # TODO: check if this works!
        if obj in self.objects:
            old_x, old_y = self.objects[obj]
            if check_empty and self.grid[y][x][-1] != EMPTY_SYMB:
                return False, move_messages[self.language]["not_empty"].substitute(object=self.grid[y][x][-1], x=x, y=y)
            if not (0 <= x < self.width and 0 <= y < self.height):
                return False, move_messages[self.language]["out_of_bounds"].substitute(x=x, y=y)
            self.grid[old_y][old_x] = self.grid[old_y][old_x][:-1]  # Remove the object from the old position
            self.grid[y][x].append(obj)  # Place the object at the new position
            self.objects[obj] = (x, y)
            return True, move_messages[self.language]["successful"].substitute(object=obj, x=x, y=y, grid=str(self))
        else:
            return False, move_messages[self.language]["obj_not_found"].substitute(object=obj)
        
    def move_rel(self, obj, dx, dy, check_empty=True):
        """
        Moves an object relative to its current position.
        :param obj: The object to move
        :param dx: The change in x-coordinate
        :param dy: The change in y-coordinate
        """
        if obj in self.objects:
            old_x, old_y = self.objects[obj]
            new_x = old_x + dx
            new_y = old_y + dy
            return self.move_abs(obj, new_x, new_y, check_empty)
        else:
            return False, move_messages["obj_not_found"].substitute(object=obj)
        
    def get_position(self, obj: str):
        """
        Returns the position of the object on the grid.
        :param obj: The object to find
        :return: A tuple (x, y) representing the position of the object
        """
        if obj in self.objects:
            return self.objects[obj]
        raise ValueError(f"Object '{obj}' not found in the grid")
        
    def compare(self, other):
        """
        Compares two grids and returns the Euclidean distance between the identical objects
        """
        if not isinstance(other, GameGrid):
            raise ValueError("Comparison is only supported between two GameGrid instances")
        if not self.object_set() == other.object_set():
            raise ValueError("Grids must have the same objects for comparison")
        
        total_distance = 0
        all_distances = {}
        for obj in self.objects:
            if obj in other.objects:
                x1, y1 = self.get_position(obj)
                x2, y2 = other.get_position(obj)
                distance = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
                all_distances[obj] = distance
                total_distance += distance
        return all_distances, total_distance


if __name__ == "__main__":
    grd = GameGrid.from_json('resources/grids/gs11x11_b7.json')
    print(grd.__str__(coords=True))