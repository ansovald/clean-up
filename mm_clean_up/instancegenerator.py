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
from typing import List, Tuple
from string import Template
from clemcore.clemgame import GameInstanceGenerator

from resources.utils.constant import ICON_WIDTH
from resources.utils.types import Icon, PositionedIcon


"""
6 variations of the game: 
- dimension 1: diff type of icons (normal, abstract, similar)
    * when normal, randomly select N normal category, from each category pick 1 icon
    * when similar, randomly select 1 normal category, from it select N icons
    * when abstract, randomly select 1 abstract category, from it select N icons
- dimension 2: diff number of icons (N = 5, 9)
"""

# LANGUAGES = ['zh-CN', 'en', 'de']
# N_INSTANCES = 3  # number of instances per experiment
# ICON_NUM_OPTIONS = [5, 9]

# # configurations for each icon type
# ICON_TYPE_CONFIGS = {
#             "normal": {
#                 "category": "normal", 
#                 "n_subcategories": "$$ICON_NUM$$",
#                 "n_icons_per_subcategory": 1,
#             }, 
#             "similar": { 
#                 "category": "normal", 
#                 "n_subcategories": 1,
#                 "n_icons_per_subcategory": "$$ICON_NUM$$",
#             }, 
#             "abstract": {
#                 "category": "abstract",
#                 "n_subcategories": 1,
#                 "n_icons_per_subcategory": "$$ICON_NUM$$",
#             }   
#         }

# -------- dev --------
LANGUAGES = ['zh-CN', 'en', 'de']
N_INSTANCES = 1
ICON_NUM_OPTIONS = [2]
ICON_TYPE_CONFIGS = {
            # "abstract": {
            #     "category": "abstract",
            #     "n_subcategories": 1,
            #     "n_icons_per_subcategory": "$$ICON_NUM$$",
            # }
            "normal": {
                "category": "normal", 
                "n_subcategories": "$$ICON_NUM$$",
                "n_icons_per_subcategory": 1,
            }, 
        }
# ---------------------


ICON_METADATA_PATH = "resources/icons/metadata.json"

# logger = logging.getLogger(__name__)
num_instance = len(ICON_TYPE_CONFIGS) * len(ICON_NUM_OPTIONS) * N_INSTANCES * len(LANGUAGES) 
print(f"will generate in total {num_instance} instances")

SEED = 73128361  # seed for reproducibility

class CleanUpMultiModalInstanceGenerator(GameInstanceGenerator):

    def __init__(self):
        super().__init__(os.path.dirname(__file__))

    def on_generate(self, seed: int, language: str):
        # for each experiment type, 
        # 1. load background

        # 2. randomly choose N_ICONS categories of icons, 
        #    and for each category, randomly choose 1 of the icons

        # 3. shuffle the selected icons twice,
        #    assemble two state per instance: [ { id, path, coord }, .. ]

        for icon_type, icon_type_config in ICON_TYPE_CONFIGS.items():
            for icon_num in ICON_NUM_OPTIONS:
                config = copy.deepcopy(icon_type_config)
                config = {key: icon_num if val == "$$ICON_NUM$$" else val for key, val in config.items() }
                e = f"{icon_type}_{icon_num}_{language}"
                
                print(f"===== Adding experiment of type {e} =====")
                print(config)

                experiment = self.add_experiment(e)

                for instance_id in range(N_INSTANCES):
                    game_instance = self.add_game_instance(experiment, instance_id)

                    self.commands = self.load_json(f'resources/commands.json')[language]
                    max_rounds = icon_num * 5      # arbitrary calculation, might change
                    max_penalties = icon_num * 3   # arbitrary calculation, might change
                    game_instance['max_rounds'] = max_rounds
                    game_instance['max_penalties'] = max_penalties
                    game_instance['lenient'] = True
                    game_instance["p1_initial_prompt"] = self.initial_prompt(language=language, max_rounds=max_rounds, max_penalties=max_penalties) + self.load_template(f'resources/initial_prompts/{language}/p1_start')
                    game_instance["p2_initial_prompt"] = self.initial_prompt(language=language, max_rounds=max_rounds, max_penalties=max_penalties) + self.load_template(f'resources/initial_prompts/{language}/p2_start')
                    game_instance['new_turn'] = self.load_template(f"resources/intermittent_prompts/{language}/new_turn")
                    game_instance['new_turn_move'] = self.load_template(f'resources/intermittent_prompts/{language}/new_turn_move')
                    game_instance['invalid_response'] = self.load_template(f'resources/intermittent_prompts/{language}/invalid_response').replace('$say', self.commands['say']).replace('$move', self.commands['move'])
                    game_instance['penalty_message'] = self.load_template(f'resources/intermittent_prompts/{language}/penalty_message')
                    game_instance['penalty_counter'] = self.load_template(f'resources/intermittent_prompts/{language}/penalty_counter')
                    game_instance['message_relay'] = self.load_template(f'resources/intermittent_prompts/{language}/message_relay')

                    keywords = self.load_json('resources/keywords.json')[language]
                    game_instance['move_pattern'] = f"(?P<head>.*){keywords['move_command']}\((?P<obj>[A-Z]), *(?P<x>\d+), *(?P<y>\d+)\)(?P<tail>.*)"
                    game_instance['message_pattern'] = f"(?P<head>.*){keywords['message_command']}\((?P<message>[^)]+)\)(?P<tail>.*)"
                    game_instance['terminate_question'] = keywords['terminate_question']    # 'finished?'
                    game_instance['terminate_answer'] = keywords['terminate_answer']        # 'finished!'
                    game_instance['restricted'] = self.load_json('resources/restricted_patterns.json')[language]
                    game_instance['parse_errors'] = self.load_json('resources/parse_errors.json')[language]

                    game_instance['move_messages'] = self.load_json('resources/move_messages.json')[language]

                    background_path = self._get_random_file(os.path.join("resources", "backgrounds"), n=1)[0]
                    game_instance["background"] = background_path

                    bg_img = Image.open(background_path)
                    bg_size = bg_img.size

                    category = config["category"]
                    n_subcategories = config["n_subcategories"]
                    n_icons_per_subcategory = config["n_icons_per_subcategory"]

                    metadata = self.load_json(ICON_METADATA_PATH)

                    assert n_subcategories <= len(metadata[category]), \
                        f"n_subcategories ({n_subcategories}) must be less than or equal to the number of subcategories in {category} ({len(metadata[category])})"

                    subcategories = random.sample(list(metadata[category].keys()), n_subcategories)

                    chosen_icons: List[Icon] = []
                    for sub in subcategories:
                        assert n_icons_per_subcategory <= len(metadata[category][sub]), \
                            f"n_icons_per_subcategory ({n_icons_per_subcategory}) must be less than or equal to the number of icons in subcategory {sub} ({len(metadata[category][sub])})"
                        
                        for icon in random.sample(metadata[category][sub], n_icons_per_subcategory):
                            chosen_icons.append(icon)
                
                    state1: List[PositionedIcon] = self._get_random_icon_state(chosen_icons, bg_size)
                    state2: List[PositionedIcon] = self._get_random_icon_state(chosen_icons, bg_size)

                    game_instance["state1"] = state1
                    game_instance["state2"] = state2


    def initial_prompt(self, language: str, max_rounds: int, max_penalties: int = 10) -> str:
        """
        Returns the initial prompt for the game.
        :param grid: The game grid
        :return: The initial prompt string
        """
        initial_prompt = Template(self.load_template(f'resources/initial_prompts/{language}/initial_prompt'))
        return initial_prompt.substitute(
            max_rounds=max_rounds,
            say=self.commands['say'],
            move=self.commands['move'],
            icon_description=self.commands['icon_description'],
            target_location_description=self.commands['target_location_description'],
            say_describe_icon_wrong=self.commands['say_describe_icon_wrong'],
            say_describe_icon_right=self.commands['say_describe_icon_right'],
            say_describe_location_wrong=self.commands['say_describe_location_wrong'],
            say_describe_location_right=self.commands['say_describe_location_right'],
            end_1=self.commands['end_1'],
            end_2=self.commands['end_2']
        )

    def invalid_response(self, language: str) -> str:
        """
        Returns the invalid response.
        :param language: language
        :return: A string of invalid response, it still contains "$reason", 
                which will be filled in GameMaster. 
        """
        invalid_response = Template(self.load_template(f'resources/intermittent_prompts/{language}/invalid_response'))
        commands = self.load_json(f'resources/commands.json')[language]
        return invalid_response.substitute(
            reason="$reason",   # ugly, I know 
            say=commands['say'],
            move=commands['move'],
        )     

    def _get_random_file(self, directory, n=1, file_extension='png') -> List[str]: 
        """
        Get the path of a random file in a given directory.
        """
        files = [f for f in os.listdir(directory) if f.lower().endswith(file_extension)]
        
        if not files:
            raise FileNotFoundError(f"No .{file_extension} files found in the directory.")
        
        assert n <= len(files), f"n must be less than or equal to the number of files in the directory ({len(files)})"

        chosen_files = random.sample(files, n) if n > 1 else [random.choice(files)]
        
        return [os.path.join(directory, p) for p in chosen_files]


    def _get_random_icon_state(self, chosen_icons: List[Icon], bg_size) -> List[PositionedIcon]: 
        """
        For each icon, additionally give them coord and an ID (for display to the players).
        """
        random.shuffle(chosen_icons)
        bg_width, bg_height = bg_size

        rand_coords: List[Tuple] = self._get_random_nonoverlapping_coords(ICON_WIDTH, 
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

    def _get_random_nonoverlapping_coords(self, icon_width, bg_width, bg_height, n) -> List[Tuple]:
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
    for language in LANGUAGES:
        print(f"Generating instances for language: {language}")
        if language == 'en': 
            file_name = 'instances.json'
        else:
            file_name = f'instances_{language}.json'
        CleanUpMultiModalInstanceGenerator().generate(filename=file_name, language=language, seed=SEED)
