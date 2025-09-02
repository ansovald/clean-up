"""Template script for instance generation.

usage:
python3 instancegenerator.py
Creates instance.json file in ./in

"""
import os
import logging

from string import Template
from clemcore.clemgame import GameInstanceGenerator
from resources.grids.game_grid import GameGrid, EMPTY_SYMB

logger = logging.getLogger(__name__)

# Seed for reproducibility
SEED = 73128361

N_INSTANCES = 2
LANGUAGES = ['en', 'zh-CN', 'de'] # maybe adding Traditional Chinese as well? 'zh-TW'
# LANGUAGES = ['zh-CN']

experiments = [
    {
        'name': 'gs7x7_obj3',
        'grid_file': 'resources/grids/gs7x7_b7.json',
        'objects': 3
    },
    {
        'name': 'gs9x9_obj5',
        'grid_file': 'resources/grids/gs9x9_b9.json',
        'objects': 5
    },
    {
        'name': 'gs11x11_obj7',
        'grid_file': 'resources/grids/gs11x11_b11.json',
        'objects': 7
    },
    {
        'name': 'gs13x13_obj9',
        'grid_file': 'resources/grids/gs13x13_b13.json',
        'objects': 9
    },
    {
        'name': 'gs15x15_obj11',
        'grid_file': 'resources/grids/gs15x15_b15.json',
        'objects': 11
    }
]

objects_by_number = {
     3: 'CLP',
     5: 'WITCH',
     7: 'POTSDAM',
     9: 'APHRODITE',
    11: 'MAGICREDFOX'
}

# # -------- dev --------
# LANGUAGES = ['de', 'zh-CN', 'en']
# N_INSTANCES = 1
# experiments = [
#     {
#         'name': 'gs7x7_obj3',
#         'grid_file': 'resources/grids/gs7x7_b2.json',
#         'objects': 'CLP'
#     }
# ]
# # ---------------------

class CleanUpInstanceGenerator(GameInstanceGenerator):
    def __init__(self):
        super().__init__(os.path.dirname(__file__))

    def on_generate(self, seed: int, language: str):
        for experiment_conf in experiments:
            experiment = self.add_experiment(f"{experiment_conf['name']}_{language}")
            for instance_id in range(N_INSTANCES):
                grid1, grid2 = GameGrid.pair_from_json(experiment_conf['grid_file'])
                show_coords = True
                objects = objects_by_number[experiment_conf['objects']]
                # Allow one penalty per object per player
                max_penalties = len(objects) * 2
                max_rounds = len(objects) * 4
                background = grid1.__str__(empty=True, show_coords=False)
                grid1.place_objects(objects)
                grid2.place_objects(objects)
                width, height = grid1.get_dimensions()
                game_instance = self.add_game_instance(experiment, instance_id)

                game_instance['language'] = language
                game_instance['width'] = width
                game_instance['height'] = height
                game_instance['lenient'] = True
                game_instance['max_penalties'] = max_penalties
                game_instance['max_rounds'] = max_rounds
                game_instance['show_coords'] = show_coords
                game_instance['empty_symbol'] = EMPTY_SYMB
                game_instance['background'] = background
                game_instance['state1'] = grid1.object_list()
                game_instance['state2'] = grid2.object_list()
                grid1.show_coords = show_coords
                grid2.show_coords = show_coords

                commands = self.load_json(f'resources/commands.json')[language]

                game_instance['p1_initial_prompt'] = self.initial_prompt(grid1, language=language, commands=commands, max_penalties=max_penalties, max_rounds=max_rounds) + self.load_template(f'resources/initial_prompts/{language}/p1_start')
                game_instance['p2_initial_prompt'] = self.initial_prompt(grid2, language=language, commands=commands, max_penalties=max_penalties, max_rounds=max_rounds) + self.load_template(f'resources/initial_prompts/{language}/p2_start')
                game_instance['new_turn'] = self.load_template(f'resources/intermittent_prompts/{language}/new_turn')
                game_instance['new_turn_move'] = self.load_template(f'resources/intermittent_prompts/{language}/new_turn_move')
                game_instance['round_counter'] = self.load_template(f'resources/intermittent_prompts/{language}/round_counter').replace('$max_rounds', str(max_rounds))
                game_instance['invalid_response'] = self.invalid_response(language)
                game_instance['penalty_message'] = self.load_template(f'resources/intermittent_prompts/{language}/penalty_message')
                game_instance['penalty_counter'] = self.load_template(f'resources/intermittent_prompts/{language}/penalty_counter')
                game_instance['message_relay'] = self.load_template(f'resources/intermittent_prompts/{language}/message_relay')

                game_instance['move_pattern'] = commands['move_pattern']
                game_instance['message_pattern'] = commands['say_pattern']

                game_instance['terminate_question'] = commands['terminate_question']    # 'finished?'
                game_instance['terminate_answer'] = commands['terminate_answer']        # 'finished!'
                game_instance['parse_errors'] = self.load_json('resources/parse_errors.json')[language]

                game_instance['move_messages'] = self.load_json('resources/move_messages.json')[language]

    def initial_prompt(self, grid: GameGrid, language: str, commands: dict, max_penalties: int = 10, max_rounds: int = 20) -> str:
        """
        Returns the initial prompt for the game.
        :param grid: The game grid
        :return: The initial prompt string
        """
        initial_prompt = Template(self.load_template(f'resources/initial_prompts/{language}/initial_prompt_unrestricted'))
        return initial_prompt.substitute(
            grid=str(grid),
            objects=grid.object_string(),
            say=commands['say'],
            move=commands['move'],
            end_1=commands['end_1'],
            end_2=commands['end_2'],
            empty_symbol=EMPTY_SYMB,
            max_penalties=max_penalties,
            max_rounds=max_rounds
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

if __name__ == '__main__':
    for language in LANGUAGES:
        logger.info(f"Generating instances for language: {language}")
        if language == 'en': 
            file_name = 'instances.json'
        else:
            file_name = f'instances_{language}.json'
        CleanUpInstanceGenerator().generate(filename=file_name, language=language, seed=SEED)
    