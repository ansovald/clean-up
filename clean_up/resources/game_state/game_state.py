from email.mime import image
from multiprocessing.util import abstract_sockets_supported
import os
from re import L
from regex import R, T
import requests
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle
import abc
from string import Template
from copy import deepcopy
from typing import Tuple, List, final, Union
from io import BytesIO
from PIL import Image
import numpy as np
import logging

from sympy import im

from resources.game_state.utils import GameObject, Icon, png_to_base64, number_to_letter, letter_to_number, EMPTY_SYMBOL, parse_grid

logger = logging.getLogger(__name__)

class GameState(abc.ABC):
    # Superclass for GridState and PicState, holding the game state for one player.
    @abc.abstractmethod
    def __init__(self, background: str, move_messages: dict = None, objects: List[GameObject] = None, img_prefix: str=None):
        self.img_prefix = img_prefix
        self.width = None
        self.height = None
        self.background = None
        self.set_background(background)
        self.move_messages = move_messages
        self.check_empty = False
        self.objects = []
        assert objects is not None, "Objects must be provided when initializing the GameState."
        self.place_objects(objects)
        self.move_log = {}  # Dictionary to keep track of moves for each object
        for obj in self.objects:
            self.move_log[obj['id']] = [tuple(obj['coord'])]

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
    def get_clean_objects(self) -> List[GameObject]:
        """
        Returns a list of all objects in the game state, but only with 'id' and 'coord' attributes.
        For PicState, it returns the value of `freepik_id` under the 'id' key.
        Only use for metric calculation!
        """
        pass

    @abc.abstractmethod
    def move_abs(self, obj: str, x: str, y: str):
        """
        This abstract method just parses the coordinates and gets the object by id.
        The actual moving logic is implemented in the subclasses.
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
        return self.object_by_id(obj), x, y

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

    def __init__(self, background: str, move_messages: dict, objects: List[Icon], img_prefix: str):
        super().__init__(background=background, move_messages=move_messages, objects=objects, img_prefix=img_prefix)
        self.image_counter = 0
        self.initial_draw = True

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

    def get_clean_objects(self) -> List[GameObject]:
        """
        Returns a list of all objects, but only with 'id' and 'coord' attributes.
        `id` key holds the actual `freepik_id`.
        Only use for metric calculation!
        """
        return [{'id': obj['freepik_id'], 'coord': obj['coord']} for obj in self.objects]

    def move_abs(self, obj, x, y):
        """
        Move the object to the absolute coordinates (x, y).
        Returns:
            success: bool, action success status
            message: str, message to be passed to the player
            image: path to the saved image
        """
        element, x, y = super().move_abs(obj, x, y)
        if element is None:
            return False, Template(self.move_messages["obj_not_found"]).substitute(object=obj), None
        if x < 0 or x > self.width or y < 0 or y > self.height:
            return False, Template(self.move_messages["out_of_bounds"]).substitute(object=obj, x=x, y=y), None
        # Update the coordinates of the object
        element['coord'] = (x, y)
        self.move_log[element['id']].append(element['coord'])
        return True, Template(self.move_messages["successful"]).substitute(object=obj, x=x, y=y), self.draw_moves(obj_id=element['id'], last_move=True, dpi=50)
    
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
    
    def draw_legend(self, icon_bounds=[0.3, 0.15, 0.6, 0.7]):
        """
        Draw a legend for the objects.
        """
        # make a plot with figsize 3x6
        fig, ax = plt.subplots(figsize=(2, 4))
        ax.axis('off')  # Hide the axes
        ax.set_title("Legend", fontsize=12, fontweight='bold')
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
                    inset_ax.text(0.1, 0.5, obj['id'], ha='left', va='center', fontsize=10, fontweight='bold')

                    icon_inset = inset_ax.inset_axes(icon_bounds)
                    icon_inset.imshow(obj['img'])
                    icon_inset.axis('off')
        plt.tight_layout()
        assert self.img_prefix is not None, "img_prefix must be set to save the image."
        # save the legend to a file
        if not os.path.exists('tmp'):
                os.makedirs('tmp')
        legend_path = f'tmp/{self.img_prefix}_legend.png'
        plt.savefig(legend_path, transparent=True)
        plt.close(fig)
        return legend_path

    def draw_image(self, dpi=100):
        """
        Draw the game state with background and objects, save it to a file and return its path.
        """
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.set_title("Your Image", fontsize=12, fontweight='bold')
        ax.imshow(self.background)
        ax.set_xticks([i for i in range(0, self.width, 50)])
        ax.set_yticks([i for i in range(0, self.height, 50)])
        ax.tick_params(labelsize=8)
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
        assert self.img_prefix is not None, "img_prefix must be set to save the image."
        # create tmp directory if it does not exist
        if not os.path.exists('tmp'):
            os.makedirs('tmp')
        filepath = f'tmp/{self.img_prefix}_state_{self.image_counter}.png'
        self.image_counter += 1
        plt.savefig(filepath, dpi=dpi, transparent=True)
        plt.close(fig)
        return filepath
    
    def draw_moves(self, obj_id=None, last_move=False, dpi=100):
        """
        Draws the two positions for each object in move_dict and connects them with an arrow.
        :param move_dict: Dictionary with object ids as keys and exactly two tuples of (x, y) coordinates as values.
        :return: List of file paths to the saved images.
        """
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.set_title("Moves", fontsize=12, fontweight='bold')
        ax.imshow(self.background)
        ax.set_xticks([i for i in range(0, self.width, 50)])
        ax.set_yticks([i for i in range(0, self.height, 50)])
        ax.tick_params(labelsize=8)
        # Fix view limits
        ax.set_xlim(0, self.width)
        ax.set_ylim(self.height, 0)  # Invert y-axis to match image

        if not obj_id:
            obj_ids = list(self.move_log.keys())
        else:
            obj_ids = [obj_id]
        
        for obj in self.objects:
            obj_id = obj['id']
            coords = self.move_log[obj_id]
            if last_move:
                if obj_id in obj_ids:
                    coords = coords[-2:]  # Only take the last two coordinates
                else:
                    coords = coords[-1:]  # Only take the last coordinate
            img = obj['img']
            w, h  = img.size
            for i, (x, y) in enumerate(coords):
                if i == len(coords) - 1:
                    # Plot the image
                    ax.imshow(img, extent=(x - w // 2, x + w // 2, y + h // 2, y - h // 2))
                circle = Circle((x, y), radius=15, color='white', fill=True)
                ax.add_patch(circle)
                ax.annotate(obj_id, xy=(x, y), ha='center', va='center', fontsize=8)
                if i > 0:  # Draw an arrow from the previous position to the current one
                    x0, y0 = coords[i - 1]
                    x1, y1 = coords[i]
                    if x0 != x1 or y0 != y1:  # Only draw an arrow if the positions are different
                        ax.annotate("", xytext=(x0, y0), xy=(x1, y1), arrowprops=dict(arrowstyle="->", color='black', lw=1.5))        
        plt.tight_layout()
        assert self.img_prefix is not None, "img_prefix must be set to save the image."
        # create tmp directory if it does not exist
        if not os.path.exists('tmp'):
            os.makedirs('tmp')
        filepath = f'tmp/{self.img_prefix}_moves.png'
        self.image_counter += 1
        plt.savefig(filepath, transparent=True, dpi=dpi)
        plt.close(fig)
        return [filepath]

    def draw(self):
        """
        Draw the game state with background and objects, save it to a file and return its path
        :param filename: Optional filename to save the figure
        """
        images = [self.draw_legend(), self.draw_image()]
        return images

class GridState(GameState):
    """
    Represents the state of a grid-based game for one player.
    """
    def __init__(self, background: str=None, move_messages: dict = None, objects: List[GameObject] = None, **kwargs):
        super().__init__(background, move_messages, objects, **kwargs)
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
        grid_str = " " + "".join([str(i+1) for i in range(self.width-2)]) + "\n"
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
                    raise ValueError(f"Cannot place object {obj['id']} at ({x}, {y}): position already occupied.")
                self.background[y][x].append(obj['id'])
                self.objects.append(obj)

    def object_string(self):
        """
        Returns a string representation of the objects in the grid.
        """
        return "'" + "', '".join(self.objects.keys()) + "'"
    
    def get_clean_objects(self) -> List[GameObject]:
        """
        Returns a list of all objects in the game state, but only with 'id' and 'coord' attributes.
        Only use for metric calculation!
        """
        return [{'id': obj['id'], 'coord': obj['coord']} for obj in self.objects]
        
    def move_abs(self, obj: str, x: str, y: str):
        """
        Move the object to the absolute coordinates (x, y).
        Returns:
            success: bool, action success status
            message: str, message to be passed to the player
            image: None, only used for PicState
        """
        logger.info(f"Moving object {obj} to ({x}, {y})")
        element, x, y = super().move_abs(obj, x, y)
        if element is None:
            return False, Template(self.move_messages["obj_not_found"]).substitute(object=obj), None
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False, Template(self.move_messages["out_of_bounds"]).substitute(object=obj, x=x, y=y), None
        if self.check_empty and self.background[y][x][-1] != EMPTY_SYMBOL:
            return False, Template(self.move_messages["not_empty"]).substitute(object=self.background[y][x][-1], x=x, y=y), None
        # Update the coordinates of the object
        old_x = element['coord'][0]
        old_y = element['coord'][1]
        self.background[old_y][old_x] = self.background[old_y][old_x][:-1]  # Remove the object from the old position
        self.background[y][x].append(obj)  # Place the object at the new position
        element['coord'] = (x, y)
        self.move_log[element['id']].append((x, y))
        return True, Template(self.move_messages["successful"]).substitute(object=obj, x=x, y=y, grid=str(self)), None
        
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
    
    def draw(self):
        return None
    

class HybridState(GridState):
    """
    Represents a hybrid state that combines both grid and picture-based game states.
    It holds two players' game states and manages moves between them.
    """
    def __init__(self, background: str, move_messages: dict, objects: List[Icon], img_prefix: str):
        super().__init__(background=background, move_messages=move_messages, objects=objects, img_prefix=img_prefix)
        logger.info(f"Initialized HybridState with img_prefix: {self.img_prefix}")

    def draw_legend(self):
        legend_text = f"Objects:\n{self.object_string()}"
        fig, ax = plt.subplots(figsize=(7.1, .8))
        ax.text(0, 0.1, legend_text, fontsize=20, ha='left', fontfamily='monospace')
        ax.set_axis_off()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        plt.show()
        assert self.img_prefix is not None, "img_prefix must be set to save the image."
        # create tmp directory if it does not exist
        if not os.path.exists('tmp'):
            os.makedirs('tmp')
        legend_path = f'tmp/{self.img_prefix}_legend.png'
        plt.savefig(legend_path, transparent=True)
        plt.close(fig)
        return legend_path
    
    def draw_image(self, dpi=100):
        """
        Draw the game state with background and objects, save it to a file and return its path.
        """
        fig, ax = plt.subplots(figsize=(3.7, 5))
        text = str(self).split('\n')
        height = len(text)
        width = len(text[2])
        for i, line in enumerate(text):
            # fill line with spaces to match width
            line = line.ljust(width)
            ax.text(0, 0.9 - i * 0.1, line, fontsize=30, ha='left', fontfamily='monospace')
        ax.set_axis_off()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        assert self.img_prefix is not None, "img_prefix must be set to save the image."
        # create tmp directory if it does not exist
        if not os.path.exists('tmp'):
            os.makedirs('tmp')
        filepath = f'tmp/{self.img_prefix}_state.png'
        plt.savefig(filepath, transparent=True, bbox_inches='tight')
        plt.close(fig)
        return filepath
    
    def draw(self):
        """
        Draw the game state with background and objects, save it to a file and return its path
        :param filename: Optional filename to save the figure
        """
        # images = [self.draw_legend(), self.draw_image()]
        return [self.draw_image()]
    
    def move_abs(self, obj: str, x: str, y: str):
        result, message, image = super().move_abs(obj, x, y)
        if result:
            image = self.draw()
        return result, message, image
    