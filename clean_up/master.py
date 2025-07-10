import re
import logging
import os.path
from typing import Dict, List, Tuple
import numpy as np
from string import Template

from clemcore.backends import Model
from clemcore.clemgame import GameSpec, GameMaster, GameBenchmark, Player, DialogueGameMaster, GameScorer, ParseError, GameError, RuleViolationError
from clemcore.clemgame.metrics import METRIC_ABORTED, METRIC_SUCCESS, METRIC_LOSE, BENCH_SCORE
# from clemcore.utils import file_utils, string_utils
from resources.grids.game_grid import GameGrid
from resources.utils.metrics import MetricPreparer, MetricCalculator, END_DISTANCE_SUM, EXPECTED_DISTANCE_SUM, MOVES, INIT_STATES, END_STATES, ingredients_registry, sub_metrics_registry #, validate

logger = logging.getLogger(__name__)

# TODO: implement strict mode. Should not end game immediately, 
#       but enforce one-command-only responses with penalties.

class Cleaner(Player):
    def __init__(self, model: Model):
        super().__init__(model)
        self._custom_responses = [
            "say(Put C in the first row and eigth column.)",
            "move(C,1,1)",
            "say(Let's move C to the top left corner.)",
            "I'm ready to go! Let's start by agreeing on a common goal state. I suggest we move all objects to the top-left corner in a specific order. Let's start by moving 'C' to the top-left corner. `move(C, 5, 5)`",
            "Let's gooo! `say(You are the best cleaner ever!)`",
            "move(C, 1, 1",
            "say(Move C to (1, 1).)",
            "move(C, 1, 1) say(I did it! C is now in the top-left corner.)",
            "haha, I love cleaning!",
            ]
        self.grid = None  # This will be set in the game master
        self._relay_message = ""

    def _custom_response(self, messages):
        response = self._custom_responses[np.random.randint(0, len(self._custom_responses))]
        return response
    
    def store_relay_message(self, message: str):
        """
        Store the relay message to add it to the next message.
        """
        self._relay_message = message

    def __call__(self, context: Dict, memorize: bool = True) -> str:
        """
        adds the relay message to the context, then calls the super class __call__ method
        """
        if self._relay_message:
            context['content'] = self._relay_message + context['content']
            self._relay_message = ""
        return super().__call__(context, memorize=memorize)


class CleanUpMaster(DialogueGameMaster):
    """
    Template class for game master.
    """
    def __init__(self, game_name: str, game_path: str, experiment: Dict, player_models: List[Model]):
        super().__init__(game_name, game_path, experiment, player_models)

    def _on_setup(self, **game_instance):
        self.game_instance = game_instance

        # Compile all regex patterns used in the game instance
        self.message_pattern = re.compile(self.game_instance['message_pattern'])
        self.move_pattern = re.compile(self.game_instance['move_pattern'])
        self.restricted = []
        for restricted in self.game_instance['restricted']:
            self.restricted.append(re.compile(restricted))

        self.player_1 = Cleaner(self.player_models[0])
        self.player_1.grid = GameGrid(self.game_instance['background'], move_messages=self.game_instance['move_messages'])
        self.player_1.grid.set_objects(self.game_instance['state1'])
        self.player_1.grid.show_coords = self.game_instance['show_coords']
        self.player_2 = Cleaner(self.player_models[1])
        self.player_2.grid = GameGrid(self.game_instance['background'], move_messages=self.game_instance['move_messages'])
        self.player_2.grid.set_objects(self.game_instance['state2'])
        self.player_2.grid.show_coords = self.game_instance['show_coords']

        self.initial_grid_string = "Player 1 grid:\n```\n" + self.player_1.grid.__str__(show_coords=self.game_instance['show_coords']) + "```\nPlayer 2 grid:\n```\n" + self.player_2.grid.__str__(show_coords=self.game_instance['show_coords']) + "```"

        self.initial_distance = self.player_1.grid.distance_sum(self.player_2.grid)

        self.add_player(self.player_1)
        self.add_player(self.player_2)

        self.finished = False   # This is for negotiating the end of the game using `terminate_question` and `terminate_answer`
        self.success = False    # True if game finished regularly
        self.terminate = False  # True if game is terminated because of rule violation or parse error
        self.aborted = False    # True if game is aborted due to a rule violation or parse error
        self.penalties = 0      # Number of collectively accumulated penalties
        self.max_penalties = self.game_instance['max_penalties']    # For strict mode, max_penalties is 0
        self.pass_turn = True
        self.max_rounds = self.game_instance['max_rounds']

        self.metric_preparer = MetricPreparer(self, self.player_1, self.player_2)

    def _on_before_game(self):
        """
        Set the initial context for the first player.
        """
        self.set_context_for(self.player_1, self.game_instance['p1_initial_prompt'])

    def _other_player(self) -> Player:
        """
        Returns the player who will be next.
        """
        other_player_idx = (self._current_player_idx + 1) % len(self.players_by_names)
        return self.get_players()[other_player_idx]

    def _check_head_tail(self, match: re.Match) -> bool:
        """
        Check if the head and tail of the match are empty.
        """
        if not self.game_instance['lenient']:
            if match.group('head') != '' or match.group('tail') != '':
                self.terminate = True
                self.aborted = True
                self.log_to_self('parse_error', "Invalid format: head or tail is not empty")
                raise ParseError(reason=self.game_instance["parse_errors"]["head_tail"], response=match.group(0))

    def _parse_response(self, player: Player, response: str) -> str:
        self.log_to_self('player_response', response)
        # TODO: for now, we will just remove backticks and newlines
        response = response.replace('`', '').replace('\n', ' ').strip()
        print(f"===== {player.name} =====")
        print(response)
        move_matches = list(self.move_pattern.finditer(response))
        message_matches = list(self.message_pattern.finditer(response))
        if len(move_matches) + len(message_matches) > 1:
            self.log_to_self('parse_error', f"Invalid response format: {response}")
            logger.warning(f"Response '{response}' contains several commands.")
            raise ParseError(reason=self.game_instance["parse_errors"]["several_commands"], response=response) #, info="Response matches both move and message patterns, which is invalid.")
        move_match = move_matches[0] if move_matches else None
        message_match = message_matches[0] if message_matches else None
        if player == self.player_1 and self.player_2._is_initial_call:
            # In this case, the command needs to be a message
            if not message_match:
                self.log_to_self('parse_error', f"Invalid response: {response}")
                logger.warning(f"Response '{response}' is not a valid message, first command must be a message.")
                raise ParseError(reason=self.game_instance["parse_errors"]["invalid_start"], response=response)
        if move_match:
            self._check_head_tail(move_match)
            return response
        if message_match:
            self._check_head_tail(message_match)
            if self.game_instance['lenient'] and message_match.group('message') == self.game_instance['terminate_answer']:
                # For now, we allow to finish the game if both players send `say(finished!)` as well, 
                # because some models are too chatty
                self.finished = True
            if message_match.group('message') == self.game_instance['terminate_question']:
                self.finished = True
            elif message_match.group('message') == self.game_instance['terminate_answer'] and self.finished:
                self.success = True
                self.terminate = True
                self.log_to_self('success', 'true')
            else:
                for restricted_pattern in self.restricted:
                    restricted_match = restricted_pattern.search(message_match.group('message'))
                    if restricted_match:
                        self.log_to_self('rule_violation', f"Response violates restriction: {restricted_pattern}")
                        logger.warning(f"Response '{response}' violates restriction: {restricted_pattern}")
                        raise ParseError(reason=self.game_instance["parse_errors"]["restriction"], response=response)
            return response
        else:
            self.log_to_self('parse_error', f"Invalid response format")
            raise ParseError(reason=self.game_instance["parse_errors"]["invalid_format"], response=response) #, info="Response does not match any expected pattern.")

    def _on_parse_error(self, error: GameError):
        if self.game_instance['lenient']:
            # In lenient mode, we just log the error and continue
            self.pass_turn = False
            self.penalties += 1
            message = self._reprompt_message(error.reason)
            self.set_context_for(self._current_player, message)
        else:
            # In strict mode, we terminate the game
            self.terminate = True
            self.aborted = True

    def _reprompt_message(self, reason) -> str:
        message = Template(self.game_instance['invalid_response']).substitute(reason=reason)
        message += '\n' + Template(self.game_instance['penalty_message']).substitute(penalty=self.penalties, max_penalties=self.max_penalties)
        return message

    def _should_pass_turn(self) -> bool:
        """
        Check if the player should pass their turn.
        """
        # time.sleep(3)
        return self.pass_turn

    def _start_next_round(self) -> bool:
        """
        :return: True, when it's the first player's turn to start a new round
        """
        if self.pass_turn:
            return self._current_player_idx == 0     
        else:
            return False

    def _advance_game(self, player: Player, parsed_response: str):
        if not parsed_response:
            raise RuleViolationError
        match = self.move_pattern.match(parsed_response)
        if match:
            obj = match.group('obj')
            x = int(match.group('x'))
            y = int(match.group('y'))
            success, message = player.grid.move_abs(obj, x, y, check_empty=True)
            self.pass_turn = success
            if success:
                self.metric_preparer.add_move((player.name, obj))
                # log the move message to the player and add it to the message history (without response)
                self.log_to_self('valid move', message)
                player.store_relay_message(message)
                # turn is passed to the other player
                next_player_prompt = self._penalty_counter_message()
                next_player_prompt += self.game_instance["new_turn_move"]
                self.set_context_for(self._other_player(), next_player_prompt)
            if not success:
                # Player is reprompted with a penalty, their turn continues. 
                self.penalties += 1
                message = message + "\n" + Template(self.game_instance['penalty_message']).substitute(penalty=self.penalties, max_penalties=self.max_penalties)
                self.log_to_self('invalid move', message)
                self.set_context_for(player, message)
                # raise RuleViolationError(f"Invalid move: {message}")
        else:
            match = self.message_pattern.match(parsed_response)
            if match:
                message = match.group('message')
                self.pass_turn = True
                player.store_relay_message(Template(self.game_instance['message_relay']).substitute(message=message))
                if player == self.player_1 and self.player_2._is_initial_call:
                    p2_initial_prompt = Template(self.game_instance['p2_initial_prompt']).substitute(
                        start_message=message
                    )
                    self.set_context_for(self.player_2, p2_initial_prompt)
                else:
                    next_player_prompt = self._penalty_counter_message()
                    next_player_prompt += Template(self.game_instance['new_turn']).substitute(turn_message=message)
                    self.set_context_for(self._other_player(), next_player_prompt)
            
    def _penalty_counter_message(self) -> str:
        """
        Returns a message with the current penalty count.
        """
        if self.max_penalties > 0:
            return Template(self.game_instance['penalty_counter']).substitute(
                penalty=self.penalties, max_penalties=self.max_penalties
            )
        # In case of strict mode (self.max_penalties == 0), we return an empty string
        return ""

    def _does_game_proceed(self):
        """
        Check if the game should continue.
        """
        if self.penalties >= self.max_penalties:
            self.log_to_self('end', 'Maximum number of penalties exceeded')
            self.aborted = True
            return False
        if self.terminate:
            return False
        if self.current_round >= self.max_rounds:  # Arbitrary limit for rounds
            logger.info("Maximum number of rounds reached, ending game.")
            self.log_to_self('end', 'Maximum number of rounds reached')
            # Reaching the maximum number of rounds is considered a success
            self.success = True
            return False
        return True

    def compute_turn_score(self):
        return 1 if self.success else 0

    def compute_episode_score(self):
        if self.success:
            return 100 / (self.current_round + 1)  # zero-based
        return 0

    def _on_after_game(self):
        ingredients = self.metric_preparer.compute_ingredients()
        # validate(ingredients_registry, ingredients, self.__class__.__name__)

        ingredients_string = ""
        for key, val in ingredients.items():
            # log all the necessary metrics to `interaction.json`
            self.log_key(key, val)
            # not display some of the ingredients in transcript
            if key not in [MOVES, INIT_STATES, END_STATES]:
                ingredients_string += f"* {key}: {float(val):.2f}\n"

        lose = not self.success
        if self.success:
            # If the game is terminated successfully, we check whether 
            # the end distance is greater than the expected distance
            lose = ingredients[END_DISTANCE_SUM] > ingredients[EXPECTED_DISTANCE_SUM]

        self.log_key(METRIC_ABORTED, int(self.aborted))
        self.log_key(METRIC_LOSE, int(lose))
        self.log_key(METRIC_SUCCESS, int(self.success))  

        # Log the grids to show up in the transcript
        self.log_to_self('initial grids', f"Initial grids:\n{self.initial_grid_string}")
        self.log_to_self('grids', f"Player 1 grid:\n```\n{self.player_1.grid.__str__(show_coords=self.game_instance['show_coords'])}\n```\nPlayer 2 grid:\n```\n{self.player_2.grid.__str__(show_coords=self.game_instance['show_coords'])}```")

        self.log_to_self('game_finished', f"* success: {self.success}\n* lose: {lose}\n* aborted: {self.aborted}\n-------\n{ingredients_string}")            
        
        # ----------------------------------------------------------
        # dev: also compute sub-metrics and bench score to show on transcript
        metrics_calculator = MetricCalculator(ingredients)
        sub_metrics, bench_score = metrics_calculator.compute_metrics()

        bench_score_string = f"* {BENCH_SCORE}: {float(bench_score):.2f}\n"

        sub_metrics_string = ""
        for key, val in sub_metrics.items(): 
            sub_metrics_string += f"* {key}: {float(val):.2f}\n"    

        self.log_to_self('dev:game_finished', f"{bench_score_string}\n-------\n{sub_metrics_string}")
        # ----------------------------------------------------------

class CleanUpScorer(GameScorer):
    def __init__(self, game_name: str, experiment: Dict, game_instance: Dict):
        super().__init__(game_name, experiment, game_instance)

    def score_turns(self, episode_interactions: Dict) -> None:
        """ Turn-level scores """
        for turn_idx in range(len(episode_interactions)):
            for event in episode_interactions[turn_idx]:
                if event['type'] == 'player_response':
                    self.log_turn_score(turn_idx, 'response_received', 1)

    def compute_episode_scores(self, episode_interactions: Dict) -> float:
        """ Compute the episode score based on the ingredients logged in interactions """
        # reconstruct ingredients from episode_interactions
        # validate(ingredients_registry, episode_interactions, self.__class__.__name__)

        ingredients = {}
        for key in ingredients_registry:
            ingredients[key] = episode_interactions[key]
        
        metrics_calculator = MetricCalculator(ingredients)
        sub_metrics, bench_score = metrics_calculator.compute_metrics()        
        # validate(sub_metrics_registry, sub_metrics, self.__class__.__name__)

        # log sub-metrics
        for key in sub_metrics:
            self.log_episode_score(key, sub_metrics[key])

        # log the bench score
        if episode_interactions[METRIC_SUCCESS]:
            # the case when game is LOSE is taken care of by MetricCalculator
            self.log_episode_score(BENCH_SCORE, bench_score) 
        else:
            logger.info(f'aborted, logging Main Score as np.nan')
            self.log_episode_score(BENCH_SCORE, np.nan)

class SomeGameBenchmark(GameBenchmark):

    def __init__(self, game_spec: GameSpec):
        super().__init__(game_spec)

    def create_game_master(self, experiment: Dict, player_models: List[Model]) -> GameMaster:
        return CleanUpMaster(self.game_name, self.game_path, experiment, player_models)

    def create_game_scorer(self, experiment: Dict, game_instance: Dict) -> GameScorer:
        return CleanUpScorer(self.game_name, experiment, game_instance)

