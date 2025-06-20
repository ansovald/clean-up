"""
Generate game instances for the Multimodal CleanUp game, making use of the icons in 'resources/icons/' 
and the backgrounds in 'resources/backgrounds/'. 

To download more icons, see 'resources/get_icons.py'.

usage:
python instancegenerator.py
Creates instance.json file in ./in

"""
import os
import re
import random
import math
import copy
from PIL import Image
from typing import List

from resources.utils.constant import ICON_WIDTH
from clemcore.clemgame import GameInstanceGenerator


"""
6 variations of the game: 
- dimension 1: diff type of icons (normal, abstract, similar)
    * when normal, randomly select N normal category, from each category pick 1 icon
    * when similar, randomly select 1 normal category, from it select N icons
    * when abstract, randomly select 1 abstract category, from it select N icons
- dimension 2: diff number of icons (N = 5, 9)
"""
# number of instances per experiment
# N_INSTANCES = 10 
N_INSTANCES = 2
# number of icons per instance; 2 is only for dev purpose
ICON_NUM_OPTIONS = [2]
# ICON_NUM_OPTIONS = [5, 9]
# configurations for each icon type
ICON_TYPE_CONFIGS = {
            "normal": {
                "category": "normal", 
                "n_subcategories": "$$ICON_NUM$$",
                "n_icons_per_subcategory": 1,
            }, 
            "similar": {  # maybe change to "normal_similar"
                "category": "normal", 
                "n_subcategories": 1,
                "n_icons_per_subcategory": "$$ICON_NUM$$",
            }, 
            # across different sub-categories of abstract, 
            # it's easy to distinguish the icons, 
            # so we only need to select one sub-category,
            "abstract": {  # maybe change to "abstract_similar"
                "category": "abstract",
                "n_subcategories": 1,
                "n_icons_per_subcategory": "$$ICON_NUM$$",
            }   
        }

ICON_METADATA_PATH = "resources/icons/metadata.json"

# logger = logging.getLogger(__name__)

random.seed(73128361)  

class CleanUPMultiModalInstanceGenerator(GameInstanceGenerator):

    def __init__(self):
        super().__init__(os.path.dirname(__file__))

    def on_generate(self):
        # for each experiment type, 
            # 1. load background

            # 2. randomly choose N_ICONS categories of icons, 
            #    and for each category, randomly choose 1 of the icons

            # 3. shuffle the selected icons, 
            #    assemble two state per instance: [ { id, path, coord }, .. ]

        for icon_type, icon_type_config in ICON_TYPE_CONFIGS.items():
            for icon_num in ICON_NUM_OPTIONS:
                config = copy.deepcopy(icon_type_config)
                config = {key: icon_num if val == "$$ICON_NUM$$" else val for key, val in config.items() }
                e = f"{icon_type}_{icon_num}"
                
                print(f"===== Adding experiment of type {e} =====")
                print(config)

                experiment = self.add_experiment(e)
                experiment['max_rounds'] = icon_num * 3
                experiment["player1_initial_prompt"] = self.load_template("resources/initial_prompts/player1")
                experiment["player2_initial_prompt"] = self.load_template("resources/initial_prompts/player2")

                experiment['feedback_say'] = self.load_template("resources/intermittent_prompts/feedback_say")
                experiment['feedback_move'] = self.load_template("resources/intermittent_prompts/feedback_move")
                experiment['feedback_other_say'] = self.load_template("resources/intermittent_prompts/feedback_other_say")
                experiment['feedback_other_move'] = self.load_template("resources/intermittent_prompts/feedback_other_move")
                experiment['feedback_ending'] = self.load_template("resources/intermittent_prompts/feedback_ending")

                experiment['terminate_question'] = "say(finished?)"
                experiment['terminate_answer'] = "say(finished!)"
                
                experiment['message_pattern'] = "say\\((?P<message>[^)]+)\\)"
                experiment['move_pattern'] = "move\\((?P<obj>[A-Z]),\\s*(?P<x>\\d+),\\s*(?P<y>\\d+)\\)"

                background_path = self._get_random_file(os.path.join("resources", "backgrounds"), n=1)[0]
                experiment["background"] = background_path

                bg_img = Image.open(background_path)
                bg_size = bg_img.size

                category = config["category"]
                n_subcategories = config["n_subcategories"]
                n_icons_per_subcategory = config["n_icons_per_subcategory"]

                print(f"Category: {category}, n_subcategories: {n_subcategories}, n_icons_per_subcategory: {n_icons_per_subcategory}")

                metadata = self.load_json(ICON_METADATA_PATH)

                target_id = 0
                while target_id < N_INSTANCES:

                    assert n_subcategories <= len(metadata[category]), \
                        f"n_subcategories ({n_subcategories}) must be less than or equal to the number of subcategories in {category} ({len(metadata[category])})"

                    subcategories = random.sample(list(metadata[category].keys()), n_subcategories)

                    # [ {id, name, url}, ... ]
                    chosen_icons = []
                    for sub in subcategories:
                        assert n_icons_per_subcategory <= len(metadata[category][sub]), \
                            f"n_icons_per_subcategory ({n_icons_per_subcategory}) must be less than or equal to the number of icons in subcategory {sub} ({len(metadata[category][sub])})"
                        
                        for icon in random.sample(metadata[category][sub], n_icons_per_subcategory):
                            chosen_icons.append(icon)
                
                    # chosen_icons = [icon
                    #                 for sub in subcategories 
                    #                     for icon in random.sample(metadata[category][sub], n_icons_per_subcategory) 
                    # ]

                    # icon_sub_dirs = self._get_random_subdir(os.path.join("resources", "icons", category), 
                    #                                         n_subcategories)
                    
                    # icon_paths = [f for d in icon_sub_dirs for f in self._get_random_file(d)]

                    # [ {id, coord, name, url, freepik_id} ]
                    state1 = self._get_random_icon_state(chosen_icons, bg_size)
                    state2 = self._get_random_icon_state(chosen_icons, bg_size)

                    game_instance = self.add_game_instance(experiment, target_id)
                    game_instance["state1"] = state1
                    game_instance["state2"] = state2
                    target_id += 1

    def _get_random_file(self, directory, n=1, file_extension='png') -> List[str]: 
        files = [f for f in os.listdir(directory) if f.lower().endswith(file_extension)]
        
        if not files:
            raise FileNotFoundError(f"No .{file_extension} files found in the directory.")
        
        assert n <= len(files), f"n must be less than or equal to the number of files in the directory ({len(files)})"

        chosen_files = random.sample(files, n) if n > 1 else [random.choice(files)]
        
        return [os.path.join(directory, p) for p in chosen_files]

    def _get_random_subdir(self, directory, k=1) -> List[str]:
        subdirs = [os.path.join(directory, d) 
                    for d in os.listdir(directory)
                        if os.path.isdir(os.path.join(directory, d))]
        if not subdirs:
            raise FileNotFoundError("No subdirectories found.")
        
        assert k < len(subdirs), "k must be less than the number of subdirectories"
        
        return random.sample(subdirs, k=k) if k > 1 else [random.choice(subdirs)]

    def _get_random_icon_state(self, chosen_icons, bg_size): 
        random.shuffle(chosen_icons)
        bg_width, bg_height = bg_size

        rand_coords = self._get_random_nonoverlapping_coords(ICON_WIDTH, 
                                                        bg_width, 
                                                        bg_height, 
                                                        len(chosen_icons))

        pattern = re.compile(rf"\.com/{ICON_WIDTH}/")
        state = []

        for idx, icon in enumerate(chosen_icons):
            # assert the icon_width bit in URL is ICON_WIDTH
            assert re.search(pattern, icon['url']) is not None

            id = chr(ord('A') + idx) # use A,B,C,D.. as ID
            
            state.append({"id": id, "coord": rand_coords[idx], **icon})

        return state

    def _get_random_nonoverlapping_coords(self, icon_width, bg_width, bg_height, n):
        w, h = icon_width, icon_width # icons are square
        step = (w // 50) * 50 # the largest multiple of 50 that is less than or equal to w

        min_x = math.ceil(w / 2 / step) * step
        max_x = (bg_width - w // 2) // step * step
        min_y = math.ceil(h / 2 / step) * step
        max_y = (bg_height - h // 2) // step * step

        valid_positions = [
            (x, y)
            for x in range(min_x, max_x + 1, step)
            for y in range(min_y, max_y + 1, step)
        ]
        assert n <= len(valid_positions)
        return random.sample(valid_positions, n)
    


if __name__ == '__main__':
    CleanUPMultiModalInstanceGenerator().generate()
