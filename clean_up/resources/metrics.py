from re import sub
from typing import Dict, List, Tuple
from statistics import harmonic_mean
from math import prod
from copy import deepcopy

# from numpy import object_

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
ALT_PENALTY_SCORE = "Alternative Penalty Score"
ALT_MAIN_SCORE = "Alternative Main Score"
sub_metrics_registry = [DISTANCE_SCORE, CONSISTENCY_SCORE, 
                        COVERAGE_SCORE]

# def validate(key_registry, to_validate: Dict, classname: str): 
#     missing = [key for key in key_registry if key not in to_validate]
#     if missing:
#         raise ValueError(f"{classname}: Missing keys: {', '.join(missing)}")

class MetricPreparer: 
    def __init__(self, gm, player_1, player_2): 
        self.moves: List[Tuple[str, str]] = []

        self.gm = gm
        self.player_1 = player_1
        self.player_2 = player_2

        # lambda functions are computing values that are not available 
        # at the initialization time
        object_count = len(player_1.game_state.objects)
        self.ingredients = {
            MOVES: self.moves,
            INIT_STATES: self.get_states(),
            END_STATES: lambda: self.get_states(),
            SHIFTS: lambda: self.compute_shifts(),
            # MAX_SHIFTS: gm.max_rounds * 2,
            MAX_SHIFTS: (object_count - 1) * 2,
            MIN_SHIFTS: object_count - 1,
            END_DISTANCE_SUM: lambda: self.player_1.game_state.distance_sum(self.player_2.game_state), 
            INIT_DISTANCE_SUM: self.gm.initial_distance, 
            EXPECTED_DISTANCE_SUM: self.player_1.game_state.expected_distance_sum(),
            PENALTIES: lambda: gm.penalties,
            MAX_PENALTIES: gm.max_penalties,
            ROUNDS: lambda: gm.current_round,
            MAX_ROUNDS: gm.max_rounds,
            OBJECT_COUNT: object_count,
        }

        # validate(ingredients_registry, self.ingredients, self.__class__.__name__)
                

    def add_move(self, move_info: Tuple[str, str]): 
        self.moves.append(move_info)

    def get_states(self) -> Dict[str, Dict[str, Tuple[str, str]]]:
        """
        Get the states of the game instance.
        Returns a dictionary with keys 'state_1' and 'state_2', 
        """
        states = {
                    'state_1': self.player_1.game_state.get_clean_objects(),
                    'state_2': self.player_2.game_state.get_clean_objects()
                }

        return states
    
    def compute_shifts(self):
        """
        Compute the number of shifts in the moves list.
        A shift is defined as a change in the targeted object 
        in every two consecutive moves.
        """
        shifts = 0
        for i in range(1, len(self.moves)): 
            _, prev_obj = self.moves[i-1]
            _, curr_obj = self.moves[i]

            if curr_obj != prev_obj: 
                shifts += 1

        return shifts


    def compute_ingredients(self): 
        """
        Compute the ingredients necessary to compute (sub) metrics.
        """
        ingredients = {key: val() if callable(val) else val for key, val in self.ingredients.items()}
        return ingredients

class MetricCalculator: 
    """
    This class centralizes the computation of all the sub-metrics, and the main metric.
    """
    def __init__(self, ingredients: Dict):
        # validate(ingredients_registry, ingredients, self.__class__.__name__)

        self.ingredients = ingredients

        self.sub_metric_funcs = {
            DISTANCE_SCORE: self.compute_distance_score,
            CONSISTENCY_SCORE: self.compute_consistency_score,
            COVERAGE_SCORE: self.compute_coverage_score
        }

        # validate(sub_metrics_registry, self.sub_metric_funcs, self.__class__.__name__)    

    def compute_distance_score(self):
        end_distance_sum = self.ingredients[END_DISTANCE_SUM]
        init_distance_sum = self.ingredients[INIT_DISTANCE_SUM]
        expected_distance_sum = self.ingredients[EXPECTED_DISTANCE_SUM]

        if end_distance_sum > expected_distance_sum: 
            # worse than random, absolutely bad, # distance_score is 0
            # game is lost, bench_score is 0
            return 0

        expected_distance_score = max(0, 1 - end_distance_sum / expected_distance_sum)
        distance_reduction_score = max(0, 1 - end_distance_sum / init_distance_sum)

        return (expected_distance_score + distance_reduction_score) / 2

    def compute_consistency_score(self):
        max_shifts = self.ingredients[MAX_SHIFTS]
        min_shifts = self.ingredients[MIN_SHIFTS]
        shifts = self.ingredients[SHIFTS]

        # in this case consistency score doesn't make sense
        # and will be taken out of bench_score
        if shifts < min_shifts: 
            return None

        # add-one smoothing
        normalized = (shifts - min_shifts) / (max_shifts + 1 - min_shifts)
        return 1 - normalized
    
    def compute_coverage_score(self):
        # Problem: can't use `id` in MM version, need freepik_id
        id_set = set([object['id'] for object in self.ingredients[INIT_STATES]['state_1']])
        moves: List[Tuple[str, str]] = self.ingredients[MOVES]
        states = self.ingredients[INIT_STATES]

        moved_obj_per_player = [set() for _ in states.keys()]
        players_recorded = list(set(move[0] for move in moves))
        
        for move in moves: 
            idx = players_recorded.index(move[0])
            moved_obj_per_player[idx].add(move[1])

        # add-one smoothing to avoid return 0
        coverage_per_player = [(len(moved_obj_set) + 1) / (len(id_set) + 1) for moved_obj_set in moved_obj_per_player]
        # return product(% of icons moved by each player)
        return prod(coverage_per_player) # we can also plug it in a monotonously increasing function on (0, 1]

    def compute_penalty_score(self):
        # We allow 2 'free' penalties for each player to account for format errors etc.
        penalties = self.ingredients[PENALTIES] - 2
        # with (penalties-2)==max_penalties, score should still be slightly above 0
        max_penalties = self.ingredients[MAX_PENALTIES] - 1
        normalized = penalties / max_penalties
        return 1 - normalized  # we can use different function at this step
    
    def alt_penalty_score(self):
        penalties = self.ingredients[PENALTIES] - 2
        max_penalties = self.ingredients[MAX_PENALTIES] - 1
        normalized = penalties / max_penalties
        return 1 / (0.5 * normalized - 1) + 2

    def compute_metrics(self): 
        sub_metrics = {name: func() for name, func in self.sub_metric_funcs.items()}

        # validate(sub_metrics_registry, sub_metrics, self.__class__.__name__)
            
        # DISTANCE_SCORE is the only sub-metric that can be 0
        # when it's 0, game is lost, bench_score is 0
        if sub_metrics[DISTANCE_SCORE] == 0:
            bench_score = 0

        if self.ingredients[SHIFTS] < self.ingredients[MIN_SHIFTS]: 
            # in this case, consistency score doesn't make sense,
            # rm consistency score to prevent it artificially drives up the bench_score
            del sub_metrics[CONSISTENCY_SCORE]
            
        penalty_score = self.compute_penalty_score()
        alt_penalty_score = self.alt_penalty_score()
        print(f"{self.ingredients[PENALTIES]}/{self.ingredients[MAX_PENALTIES]}, {penalty_score:.2f} -> {alt_penalty_score:.2f}")
        

        # Take the harmonic mean of the sub-metrics, and multiply by the penalty score
        bench_score = harmonic_mean(sub_metrics.values()) * penalty_score * 100
        # bench_score = sub_metrics[DISTANCE_SCORE] * penalty_score * 100

        sub_metrics[PENALTY_SCORE] = penalty_score
        sub_metrics[ALT_PENALTY_SCORE] = alt_penalty_score
        sub_metrics[ALT_MAIN_SCORE] = sub_metrics[DISTANCE_SCORE] * alt_penalty_score * 100

        # overwrite MAX_SHIFT for existing interactions.json file
        self.ingredients[MAX_SHIFTS] = self.ingredients[MIN_SHIFTS] * 2 

        return sub_metrics, bench_score, self.ingredients