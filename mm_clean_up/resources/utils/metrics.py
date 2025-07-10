from typing import Dict, List, Tuple
from statistics import harmonic_mean
from math import prod
from resources.utils.types import PositionedIcon, FullPositionedIcon

# ingredients to compute sub-metrics 
MOVES = "Moves"
INIT_STATES = "Init States"
END_STATES = "End States"
SHIFTS = "Shifts"
MAX_SHIFTS = "Max Shifts"
MIN_SHIFTS = "Min Shifts"
END_DISTANCE_SUM = "End Distance Sum"
INIT_DISTANCE_SUM = "Init Distance Sum"
EXPECTED_DISTANCE_SUM = "Expected Distance Sum"
PENALTIES = "Penalties"
MAX_PENALTIES = "Max Penalties"
OBJECT_COUNT = "Object Count"
ROUNDS = "Rounds"
MAX_ROUNDS = "Max Rounds"
ingredients_registry = [MOVES, INIT_STATES, END_STATES,
                        SHIFTS, MAX_SHIFTS, MIN_SHIFTS, 
                        END_DISTANCE_SUM, INIT_DISTANCE_SUM, EXPECTED_DISTANCE_SUM,
                        PENALTIES, MAX_PENALTIES, ROUNDS, MAX_ROUNDS,
                        OBJECT_COUNT]

# sub-metrics
DISTANCE_SCORE = "Distance Score"
CONSISTENCY_SCORE = "Consistency Score"
COVERAGE_SCORE = "Coverage Score"
PENALTY_SCORE = "Penalty Score"
sub_metrics_registry = [DISTANCE_SCORE, CONSISTENCY_SCORE, 
                        COVERAGE_SCORE]


class MetricPreparer: 
    """

    """
    def __init__(self, gm, player_1, player_2): 
        self.moves: List[Tuple[str, PositionedIcon]] = []

        self.gm = gm
        self.player_1 = player_1
        self.player_2 = player_2
        self.icon_attrs = PositionedIcon.__annotations__.keys()

        self.ingredients = {
            MOVES: self.moves,
            INIT_STATES: {k:v for k, v in gm.game_instance.items() if k in ['state1', 'state2']},
            END_STATES: lambda: self.get_end_states(),
            SHIFTS: lambda: self.compute_shifts(),
            MAX_SHIFTS: lambda: gm.current_round * 2,
            MIN_SHIFTS: len(player_1.pic_state.state) - 1,
            END_DISTANCE_SUM: lambda: self.player_1.pic_state.distance_sum(self.player_2.pic_state), 
            INIT_DISTANCE_SUM: self.gm.initial_distance, 
            EXPECTED_DISTANCE_SUM: self.player_1.pic_state.expected_distance_sum(),
            PENALTIES: lambda: gm.penalties,
            MAX_PENALTIES: gm.max_penalties,
            ROUNDS: lambda: gm.current_round,
            MAX_ROUNDS: gm.max_rounds,
            OBJECT_COUNT: len(player_1.pic_state.state),
        }

    def add_move(self, move_info: Tuple[str, FullPositionedIcon]): 
        """
        Strip the unnecessary keys from the move_info tuple and add it to the moves list.
        move_info: a tuple: (player_name, { id, coord, name, url, freepik_id, img } )
        """
        cleaned_icon_info: PositionedIcon = self.get_cleaned_icon(move_info[1])
        self.moves.append((move_info[0], cleaned_icon_info))

    def get_cleaned_icon(self, icon: FullPositionedIcon) -> PositionedIcon:
        """
        Strip the unnecessary keys from the FullPositionedIcon and return a PositionedIcon.
        FullPositionedIcon contains an additional key 'img', 
        the value of which is an PNGImage object and should be removed for JSON serialization..
        """
        return {key: icon[key] for key in self.icon_attrs if key in icon}

    def get_end_states(self) -> Dict[str, List[PositionedIcon]]:
        """
        Get the end states of the game instance.
        Returns a dictionary with keys 'state1' and 'state2', 
        each containing a list of FullPositionedIcon objects.
        """
        end_states = {
                        'state1': [self.get_cleaned_icon(ele) for ele in self.player_1.pic_state.state],
                        'state2': [self.get_cleaned_icon(ele) for ele in self.player_2.pic_state.state]
                    }

        return end_states
    
    def compute_shifts(self):
        """
        Compute the number of shifts in the moves list.
        A shift is defined as a change in the freepik_id of the PositionedIcon
        in every two consecutive moves.
        """
        shifts = 0
        for i in range(1, len(self.moves)): 
            _, prev_icon = self.moves[i-1]
            _, curr_icon = self.moves[i]
            prev_icon: PositionedIcon
            curr_icon: PositionedIcon

            if curr_icon['freepik_id'] != prev_icon['freepik_id']: 
                shifts += 1

        return shifts


    def compute_ingredients(self): 
        """
        Compute the ingredients necessary to compute (sub) metrics.
        """
        for ingredients in ingredients_registry:
            if ingredients not in self.ingredients:
                raise ValueError(f"MetricPreparer: {ingredients} is not in the ingredients registry.")
            
        ingredients = {key: val() if callable(val) else val for key, val in self.ingredients.items()}

        return ingredients

class MetricCalculator: 
    """
    This class centralizes the computation of all the sub-metrics, and the main metric.
    """
    def __init__(self, ingredients: Dict):
        self.ingredients = ingredients

        for key in ingredients_registry: 
            if key not in self.ingredients: 
                raise ValueError(f"MetricCalculator: Key '{key}' is not in the ingredients.")

        self.sub_metric_funcs = {
            DISTANCE_SCORE: self.compute_distance_score,
            CONSISTENCY_SCORE: self.compute_consistency_score,
            COVERAGE_SCORE: self.compute_coverage_score
        }        

    def compute_distance_score(self):
        end_distance_sum = self.ingredients[END_DISTANCE_SUM]
        init_distance_sum = self.ingredients[INIT_DISTANCE_SUM]
        expected_distance_sum = self.ingredients[EXPECTED_DISTANCE_SUM]

        if end_distance_sum > expected_distance_sum: 
            # worse than random, absolutely bad, # distance_score is 0
            # game is lost, bench_score is 0
            return 0

        # expected_distance_score = max(0, 1 - end_distance_sum / expected_distance_sum)
        # distance_reduction_score = max(0, 1 - end_distance_sum / init_distance_sum)

        # return (expected_distance_score + distance_reduction_score) / 2
        expected_distance_score = max(0, 1 - end_distance_sum / expected_distance_sum)
        return expected_distance_score

    def compute_consistency_score(self):
        max_shifts = self.ingredients[MAX_SHIFTS]
        min_shifts = self.ingredients[MIN_SHIFTS]
        shifts = self.ingredients[SHIFTS]

        # when the players don't cover all the icons, return the best score 1
        # we will capture this error with another metric, Coverage Score
        if shifts < min_shifts: 
            return 1

        # add-one smoothing
        normalized = (shifts - min_shifts) / (max_shifts + 1 - min_shifts)
        return 1 - normalized
    
    def compute_coverage_score(self):
        id_set = set([ele['freepik_id'] for ele in self.ingredients[INIT_STATES]['state1']])
        moves: List[Tuple[str, PositionedIcon]] = self.ingredients[MOVES]

        unique_players = list(set(move[0] for move in moves))
        moved_obj_per_player = [set() for _ in unique_players]
        
        for move in moves: 
            idx = unique_players.index(move[0])
            moved_obj_per_player[idx].add(move[1]['freepik_id'])

        # add-one smoothing to avoid return 0
        coverage_per_player = [(len(moved_obj_set) + 1) / (len(id_set) + 1) for moved_obj_set in moved_obj_per_player]
        # return product(% of icons moved by each player)
        return prod(coverage_per_player) # we can also plug it in a monotonously increasing function on (0, 1]

    def compute_penalty_score(self):     
        penalties = self.ingredients[PENALTIES]
        max_penalties = self.ingredients[MAX_PENALTIES]
        normalized = penalties / max_penalties
        return 1 - normalized  # we can use different function at this step

    def compute_metrics(self): 
        sub_metrics = {name: func() for name, func in self.sub_metric_funcs.items()}

        for key in sub_metrics_registry:
            if key not in sub_metrics:
                raise ValueError(f"MetricCalculator: Key '{key}' is not in the sub-metrics registry.")
            
        # DISTANCE_SCORE is the only sub-metric that can be 0
        # when it's 0, game is lost, bench_score is 0
        if sub_metrics[DISTANCE_SCORE] == 0:
            bench_score = 0

        penalty_score = self.compute_penalty_score()

        # Take the harmonic mean of the sub-metrics, and multiply by the penalty score
        bench_score = harmonic_mean(sub_metrics.values()) * penalty_score

        sub_metrics[PENALTY_SCORE] = penalty_score

        return sub_metrics, bench_score