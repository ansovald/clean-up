"""Template script for instance generation.

usage:
python3 instancegenerator.py
Creates instance.json file in ./in

"""
from math import exp
import os
import logging
import json
import random
from copy import deepcopy
from shutil import move
from string import Template

from numpy import empty, object_
from clemcore.clemgame import GameInstanceGenerator
from resources.game_state.utils import EMPTY_SYMBOL, place_objects, GameObject
from resources.game_state.game_state import GridState

logger = logging.getLogger(__name__)

# Seed for reproducibility
SEED = 73128361
ICON_METADATA_PATH = "resources/icons/metadata.json"

class CleanUpInstanceGenerator(GameInstanceGenerator):
    def __init__(self):
        super().__init__(os.path.dirname(__file__))

    def on_generate(self, seed, config, n_instances, language, modality, **kwargs):
        print(f"Generating instances for language '{language}' and modality '{modality}'")
        self.modality = modality
        self.objects = config['objects']
        self.language = language
        self.initial_prompt = Template(self.load_template(f'resources/initial_prompts/{language}/initial_prompt_{modality}'))
        self.p1_start = self.load_template(f'resources/initial_prompts/{language}/p1_start')
        self.p2_start = self.load_template(f'resources/initial_prompts/{language}/p2_start')
        self.commands = self.load_json('resources/commands.json')
        move_messages = self.load_json('resources/move_messages.json')
        parse_errors = self.load_json('resources/parse_errors.json')
        intermittent_prompts = self.load_json('resources/intermittent_prompts.json')
        intermittent_prompts['invalid_response'] = Template(intermittent_prompts['invalid_response']).safe_substitute(
            say=self.commands['say'],
            move=self.commands['move'],
            empty_symbol=EMPTY_SYMBOL
        )
        self.examples = self.load_json('resources/examples.json')
        template_instance = {
            "intermittent_prompts": intermittent_prompts,
            "say_pattern": self.commands['say_pattern'],
            "move_pattern": self.commands['move_pattern'],
            "parse_errors": parse_errors,
            "move_messages": move_messages,
            "terminate_question": self.commands['terminate_question'],
            "terminate_answer": self.commands['terminate_answer']
        }

        restricted_patterns = self.load_json('resources/restricted_patterns.json')
        if restricted_patterns:
            template_instance["restricted_patterns"] = restricted_patterns

        for experiment_conf in config['experiments']:
            for object_count in config['objects']:
                if modality == 'image':
                    self.current_experiment_conf = {key: object_count if val == 'OBJECT_COUNT' else val for key, val in experiment_conf.items()}
                else:
                    self.current_experiment_conf = experiment_conf
                experiment_name = f"{experiment_conf['name']}_{object_count}obj_{language}"
                experiment = self.add_experiment(experiment_name)
                max_penalties = config['penalty_factor'] * int(object_count)
                max_rounds = int(object_count) * 4
                for instance_id in range(n_instances):
                    game_instance = self.add_game_instance(experiment, instance_id)
                    # TODO: Do I need to pass modality?
                    game_instance['modality'] = modality
                    game_instance['language'] = language
                    game_instance['max_penalties'] = max_penalties
                    game_instance['max_rounds'] = max_rounds
                    if modality == 'text':
                        game_instance['empty_symbol'] = EMPTY_SYMBOL
                    self.background = self.sample_background()
                    game_instance['background'] = self.background
                    objects_1 = self.get_objects(object_count)
                    objects_2 = deepcopy(objects_1)
                    for key in template_instance:
                        game_instance[key] = template_instance[key]
                    game_instance['intermittent_prompts']['penalty_counter'] = Template(game_instance['intermittent_prompts']['penalty_counter']).safe_substitute(max_penalties=max_penalties)
                    game_instance['state_1'] = place_objects(self.modality, objects_1, game_instance['background'])
                    game_instance['state_2'] = place_objects(self.modality, objects_2, game_instance['background'])
                    
                    object_string = None
                    grid_1 = None
                    grid_2 = None
                    if modality == 'text':
                        object_string = "'" + "', '".join([obj['id'] for obj in objects_1]) + "'"
                        grid_1 = str(GridState(self.background, objects=objects_1))
                        grid_2 = str(GridState(self.background, objects=objects_2))
                    
                    p1_initial_prompt = self.prepare_initial_prompt(grid=grid_1, max_penalties=max_penalties, max_rounds=max_rounds, object_string=object_string)
                    if not grid_2:
                        p2_initial_prompt = p1_initial_prompt
                    else:
                        p2_initial_prompt = self.prepare_initial_prompt(grid=grid_2, max_penalties=max_penalties, max_rounds=max_rounds, object_string=object_string)
                    game_instance['p1_initial_prompt'] = p1_initial_prompt + self.p1_start
                    game_instance['p2_initial_prompt'] = p2_initial_prompt + self.p2_start

    def load_json(self, file_path: str) -> dict:
        """Load a JSON file from the game directory."""
        data = super().load_json(file_path)
        if self.language in data:
            data = data[self.language]
        if self.modality in data:
            data = data[modality]
        else:
            for key in data:
                if isinstance(data[key], dict) and self.modality in data[key]:
                    data[key] = data[key][self.modality]
        return data
    
    def sample_background(self):
        """
        Samples a background (text grid) from the provided dictionary.
        Might implement sampling background images in the future.
        """
        if modality == 'text':
            backgrounds = self.load_json('resources/backgrounds/grids.json')[self.current_experiment_conf['grid_config']]
            background = random.choice(list(backgrounds.values()))
        else:
            background = 'resources/backgrounds/kitchen.png'
        return background
    
    def fill_grid(self, grid, objects):
        """
        Fills the grid with objects.
        For text modality, it places objects in the grid.
        """
        assert self.modality == 'text', "This method is only implemented for text modality."
        width = grid.index('\n')
        for obj in objects:
            x, y = obj['coord']
            print(f"Placing object {obj['id']} at ({x}, {y})")
            x += 1  # Adjust for frame
            # map to index in grid string
            index = y * (width + 1) + x
            if index < len(grid):
                grid = grid[:index] + obj['id'] + grid[index + 1:]
        print(grid)
        return grid

    
    def get_objects(self, object_count):
        objects = []
        if self.modality == 'text':
            for letter in self.objects[object_count]:
                object = GameObject(id=letter, coord=(None, None))
                objects.append(object)
        else:
            metadata = self.load_json(ICON_METADATA_PATH)
            colored = self.current_experiment_conf['colored']
            if colored:  # sampling colored icons
                category_sample_base = [key for key in metadata.keys() if set(metadata[key].keys()) != set(['black'])]
            else:  # sampling black icons
                category_sample_base = [key for key in metadata.keys() if 'black' in metadata[key]]

            sampled_categories = random.sample(category_sample_base, k=int(object_count))
            for category in sampled_categories:
                if colored:
                    color = random.choice(list(set(metadata[category].keys()) - set(['black'])))
                else:
                    color = 'black'
                for icon in random.sample(metadata[category][color], k=int(self.current_experiment_conf['objects_per_color'])):
                    objects.append(icon)
        return objects

    def prepare_initial_prompt(self, max_penalties, max_rounds, grid=None, object_string=None) -> str:
        initial_prompt = self.initial_prompt.safe_substitute(
            grid=grid,
            objects=object_string,
            max_rounds=max_rounds,
            max_penalties=max_penalties,
            say=self.commands['say'],
            move=self.commands['move'],
            end_1=self.commands['end_1'],
            end_2=self.commands['end_2'],
            empty_symbol=EMPTY_SYMBOL,
            **self.examples
        )
        return initial_prompt

    
if __name__ == '__main__':
    experiments = json.load(open('resources/experiments.json', 'r', encoding='utf-8'))
    n_instances = experiments.get('n_instances', 2)
    for language in experiments['languages']:
        for modality in experiments['modalities']:
            logger.info(f"Generating instances for modality '{modality}' and language {language}")
            file_name = experiments['modalities'][modality].get('instances', 'instances')
            if language == 'en':
                file_name = file_name + '.json'
            else:
                file_name = f"{file_name}_{language}.json"
            config = experiments['modalities'][modality]
            CleanUpInstanceGenerator().generate(filename=file_name, language=language, modality=modality, config=config, n_instances=n_instances, seed=SEED)
