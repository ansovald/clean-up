from multiprocessing.util import abstract_sockets_supported
import os
from re import L
from regex import R, T
import requests
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import abc
from string import Template
from copy import deepcopy
from typing import Tuple, List, final, Union
from io import BytesIO
from PIL import Image
import numpy as np

from resources.game_state.utils import GameObject, Icon, png_to_base64, number_to_letter, letter_to_number, EMPTY_SYMBOL, parse_grid

class GameState(abc.ABC):
    # Superclass for GridState and PicState, holding the game state for one player.
    @abc.abstractmethod
    def __init__(self, background: str, move_messages: dict = None, objects: List[GameObject] = None):
        self.width = None
        self.height = None
        self.background = None
        self.set_background(background)
        self.move_messages = move_messages
        self.check_empty = False
        self.objects = []
        self.place_objects(objects)

    @abc.abstractmethod
    def set_background(self, background: str):
        # sets background, width, and height
        pass
    
    @abc.abstractmethod
    def place_objects(self, objects: List[GameObject]) -> List[GameObject]:
        pass

    @final
    def object_by_id(self, obj_id: str) -> Union[GameObject, None]:
        for obj in self.objects:
            if obj['id'] == obj_id:
                return obj
        return None

    @abc.abstractmethod
    def move_abs(self, obj: str, x: str, y: str):
        """
        Move an object to an absolute position (x, y).
        :param obj: id of the object to move
        :param x: The x-coordinate
        :param y: The y-coordinate
        :return: A tuple (success, message)
        """
        pass

    @final
    def distance_sum(self, other):
        """
        Calculate the sum of distances between this object and another object.
        :param other: The other object
        :return: The sum of distances
        """
        # Make sure both objects are of the same (sub)class
        if not isinstance(other, self.__class__):
            raise TypeError(f"Cannot compare {self.__class__.__name__} with {other.__class__.__name__}")
        distances = self.get_pairwise_distances(other.objects)
        return sum(distances.values())

    @abc.abstractmethod
    def get_pairwise_distances(self, other_objects: List[GameObject]) -> dict:
        """
        Get pairwise distances between the object and all other objects.
        :param obj: The object to compare distances with
        :return: A dictionary of distances
        """
        pass
    
    @final
    def expected_distance_sum(self):
        """
        Returns the expected total distance for a given number of objects, 
        when they are randomly distributed on the background.
        """
        if self.width is None or self.height is None:
            raise ValueError("Width and height must be set before calculating expected distance sum.")
        avg_x_dist = (self.width ** 2 - 1) / (3 * self.width)
        avg_y_dist = (self.height ** 2 - 1) / (3 * self.height)
        avg_dist = (avg_x_dist ** 2 + avg_y_dist ** 2) ** 0.5
        return avg_dist * len(self.objects)
    
    @final
    def euclidean_distance(self, coord1: Tuple[int, int], coord2: Tuple[int, int]) -> float:
        """
        Calculate the Euclidean distance between two coordinates.
        :param coord1: The first coordinate (x1, y1)
        :param coord2: The second coordinate (x2, y2)
        :return: The Euclidean distance
        """
        x1, y1 = coord1
        x2, y2 = coord2
        return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


class PicState(GameState):
    """
    Represents the state of a picture-based game for one player.
    """

    def __init__(self, background: str, move_messages: dict, objects: List[Icon], img_prefix: str = None):
        super().__init__(background, move_messages, objects)
        self.img_prefix = img_prefix
        self.image_counter = 0

    def set_background(self, background: str):
        """
        Set the background image for the game state.
        :param background: Path to the background image
        """
        if not os.path.exists(background):
            raise FileNotFoundError(f"Background image '{background}' does not exist.")
        self.background = Image.open(background)
        self.width, self.height = self.background.size
        self.background = np.asarray(self.background)

    def place_objects(self, objects: List[Icon]):
        """
        Place objects on the background image.
        :param objects: List of Icon objects to place
        :return: List of placed Icon objects
        """
        for obj in objects:
            obj_copy = deepcopy(obj)
            response = requests.get(obj_copy['url'])
            response.raise_for_status()
            obj_copy['img'] = Image.open(BytesIO(response.content))
            self.objects.append(obj_copy)

    def move_abs(self, obj, x, y):
        """
        Move the object to the absolute coordinates (x, y).
        Returns:
            success: bool, action success status
            message: str, message to be passed to the player
        """
        if isinstance(x, str):
            try:
                x = int(x)
            except ValueError:
                raise ValueError(f"Invalid x-coordinate: {x}. It should be an integer.")
        if isinstance(y, str):
            try:
                y = int(y)
            except ValueError:
                raise ValueError(f"Invalid y-coordinate: {y}. It should be an integer.")
        element = self.object_by_id(obj)
        if element is None:
            return False, Template(self.move_messages["obj_not_found"]).substitute(object=obj)
        if x < 0 or x > self.width or y < 0 or y > self.height:
            return False, Template(self.move_messages["out_of_bounds"]).substitute(object=obj, x=x, y=y)
        # Update the coordinates of the object
        element['coord'] = (x, y)
        return True, Template(self.move_messages["successful"]).substitute(object=obj, x=x, y=y)
    
    def get_pairwise_distances(self, other_objects):
        distances = {}
        for obj in self.objects:
            # freepik_id is the real unique identifier 
            freepik_id = obj['freepik_id']
            for other_obj in other_objects:
                if other_obj['freepik_id'] == freepik_id:
                    dist = self.euclidean_distance(obj['coord'], other_obj['coord'])
                    distances[other_obj['id']] = dist
        return distances
    
    def plot_image(self, ax):
        """
        Plot background image with labeled axes and objects.
        """
        ax.imshow(self.background)
        ax.set_xticks([i for i in range(0, self.width, 50)])
        ax.set_yticks([i for i in range(0, self.height, 50)])
        # Fix view limits
        ax.set_xlim(0, self.width)
        ax.set_ylim(self.height, 0)  # Invert y-axis to match image

        # Overlay objects
        for obj in self.objects:
            x, y = obj['coord']
            img = obj['img']
            w, h  = img.size
            ax.imshow(obj['img'], extent=(x - w // 2, x + w // 2, y + h // 2, y - h // 2))
        
        plt.tight_layout()
    
    def plot_legend(self, ax, icon_bounds=[0.2, 0.15, 0.7, 0.7]):
        """
        Plot a legend for the objects.
        """
        rows = 3
        obj_count = len(self.objects)
        columns = int(np.ceil(obj_count / rows))

        for r in range(rows):
            for c in range(columns):
                idx = r * columns + c
                if idx < obj_count:
                    obj = self.objects[idx]
                    inset_ax = ax.inset_axes([c / columns, 1 - (r + 1) / rows, 1 / columns, 1 / rows * 0.85])
                    inset_ax.axis('off')
                    inset_ax.add_patch(FancyBboxPatch((0.05, 0.05), 0.9, 0.9, boxstyle="round,pad=0.0, rounding_size=0.1", linewidth=0, facecolor='lightgrey'))
                    inset_ax.text(0.1, 0.5, obj['id'], ha='left', va='center', fontsize=15, fontweight='bold')

                    icon_inset = inset_ax.inset_axes(icon_bounds)
                    icon_inset.imshow(obj['img'])
                    icon_inset.axis('off')
        plt.tight_layout()

    def draw(self):
        """
        Draw the game state with background and objects, save it to a file and return its path
        :param filename: Optional filename to save the figure
        """
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.axis('off')  # Hide the axes
        gs = fig.add_gridspec(1, 2, width_ratios=[2, 1])  # 2:1 ratio
        
        ax1 = fig.add_subplot(gs[0])
        ax2 = fig.add_subplot(gs[1])  
        ax2.axis('off')
        self.plot_image(ax1)
        self.plot_legend(ax2)
        plt.tight_layout()
        if self.img_prefix:
            # create tmp directory if it does not exist
            if not os.path.exists('tmp'):
                os.makedirs('tmp')
            filepath = f'tmp/{self.img_prefix}_pic_state_{self.image_counter}.png'
            self.image_counter += 1
            plt.savefig(filepath, bbox_inches='tight', pad_inches=0.1)
            plt.close(fig)
            return filepath
        else:
            plt.close(fig)
            raise ValueError("img_prefix must be set to save the image.")


class GridState(GameState):
    """
    Represents the state of a grid-based game for one player.
    """
    def __init__(self, background: str, move_messages: dict = None, objects: List[GameObject] = None):
        super().__init__(background, move_messages, objects)
        self.check_empty = True

    def set_background(self, background: str):
        """
        Set the background grid for the game state.
        :param background: The grid string representation
        """
        self.background = parse_grid(background)
        self.width = len(self.background[0])
        self.height = len(self.background)

    def __str__(self, empty=False):
        """
        Returns a string representation of the grid.
        :param empty: don't show objects if True
        :return: String representation of the grid
        """
        grid_str = " " + "".join([number_to_letter(i+1) for i in range(self.width-2)]) + "\n"
        i = 0 if empty else -1
        for j, row in enumerate(self.background):
            grid_str += ''.join([cell[i] for cell in row])
            if not (j == 0 or j == len(self.background) - 1):
                grid_str += f" {j}"
            grid_str += '\n'
        return grid_str

    def place_objects(self, objects: List[GameObject]):
        """
        Place objects on the grid.
        :param objects: List of GameObject to place
        :return: List of placed GameObject
        """
        self.objects = []
        for obj in objects:
            x, y = obj['coord']
            x = int(x)
            y = int(y)
            if 0 <= x < self.width and 0 <= y < self.height:
                if self.background[y][x][-1] != EMPTY_SYMBOL:
                    print(str(self))
                    raise ValueError(f"Cannot place object {obj['id']} at ({x}, {y}): position already occupied.")
                self.background[y][x].append(obj['id'])
                self.objects.append(obj)

    def object_string(self):
        """
        Returns a string representation of the objects in the grid.
        """
        return "'" + "', '".join(self.objects.keys()) + "'"
    
    def move_abs(self, obj: str, x: str, y: str):
        """
        Move the object to the absolute coordinates (x, y).
        Returns:
            success: bool, action success status
            message: str, message to be passed to the player
        """
        x_letter = x
        if isinstance(x, str):
            try:
                x = letter_to_number(x)
            except ValueError:
                raise ValueError(f"Invalid x-coordinate: {x}. It should be a lowercase letter.")
        if isinstance(y, str):
            try:
                y = int(y)
            except ValueError:
                raise ValueError(f"Invalid y-coordinate: {y}. It should be an integer.")
        element = self.object_by_id(obj)
        if element is None:
            return False, Template(self.move_messages["obj_not_found"]).substitute(object=obj)
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False, Template(self.move_messages["out_of_bounds"]).substitute(object=obj, x=x_letter, y=y)
        # Update the coordinates of the object
        old_x = element['coord'][0]
        old_y = element['coord'][1]
        self.background[old_y][old_x] = self.background[old_y][old_x][:-1]  # Remove the object from the old position
        self.background[y][x].append(obj)  # Place the object at the new position
        element['coord'] = (x, y)
        return True, Template(self.move_messages["successful"]).substitute(object=obj, x=x_letter, y=y)
        
    def get_pairwise_distances(self, other_objects):
        distances = {}
        for obj in self.objects:
            # ID is the unique identifier
            obj_id = obj['id']
            for other_obj in other_objects:
                if other_obj['id'] == obj_id:
                    dist = self.euclidean_distance(obj['coord'], other_obj['coord'])
                    distances[other_obj['id']] = dist
        return distances