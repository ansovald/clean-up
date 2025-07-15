from typing import Dict, List, Tuple
from statistics import harmonic_mean
import math
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
ROUNDS = "Rounds"
MAX_ROUNDS = "Max Rounds"
OBJECT_COUNT = "Object Count"
PLAYERS = "Players"
ingredients_registry = [MOVES, INIT_STATES, END_STATES,
                        SHIFTS, MAX_SHIFTS, MIN_SHIFTS, 
                        END_DISTANCE_SUM, INIT_DISTANCE_SUM, EXPECTED_DISTANCE_SUM,
                        PENALTIES, MAX_PENALTIES, ROUNDS, MAX_ROUNDS,
                        OBJECT_COUNT, PLAYERS]

# sub-metrics
DISTANCE_SCORE = "Distance Score"
CONSISTENCY_SCORE = "Consistency Score"
COVERAGE_SCORE = "Coverage Score"
PENALTY_SCORE = "Penalty Score"
sub_metrics_registry = [DISTANCE_SCORE, CONSISTENCY_SCORE, 
                        COVERAGE_SCORE, PENALTY_SCORE]


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
            # MAX_SHIFTS: lambda: gm.current_round * 2,
            MAX_SHIFTS: (len(player_1.pic_state.state) - 1)*2,
            MIN_SHIFTS: len(player_1.pic_state.state) - 1,
            END_DISTANCE_SUM: lambda: self.player_1.pic_state.distance_sum(self.player_2.pic_state), 
            INIT_DISTANCE_SUM: self.gm.initial_distance, 
            EXPECTED_DISTANCE_SUM: self.player_1.pic_state.expected_distance_sum(),
            PENALTIES: lambda: gm.penalties,
            MAX_PENALTIES: gm.max_penalties,
            ROUNDS: lambda: gm.current_round,
            MAX_ROUNDS: gm.max_rounds,
            OBJECT_COUNT: len(player_1.pic_state.state),
            PLAYERS: [player_1.name, player_2.name]
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
            COVERAGE_SCORE: self.compute_coverage_score,
            PENALTY_SCORE: self.compute_penalty_score
        }
        
        # these 3 functions follow (smaller ingredients -> higher score)
        self.distance_score_func = None
        self.consistency_score_func = None
        self.penalty_score_func = None
        # this function follows (bigger ingredient -> higher score)
        self.coverage_score_func = None

    @staticmethod
    def function_factory(anchor, x_bad, y_bad, monoDecr=True): 
        """
        Returns a function f such that, for a given ingredient (eg. end_distance_sum, focus_shift, penalties)
        f is an exponential function that satisfies f(anchor) = 1, f(x_bad) = y_bad
        Params: 
        - anchor: the input ingredient that would achieve output (sub)metric 1
        - (x_bad, y_bad): represent a undesired input ingredient x_bad that would achieve score y_bad
        - monoDecr: True if f should be a monotonously decreasing function 
        ========================================================
        new idea: **dynamically create the scoring function**!!
        ========================================================
        Old problem:
        - Had problem defining max_shift in consistency_score,
        - also, the add-one smoothing means different scale when number of objects differs
        - (text-only) scores are inflated
        Let's make it generic:
            we want a scoring function f that: 
            f(min_value) = 1
            f(x_bad) = y_bad, where x_bad is a bad enough ingredient(eg. a big end_distance_sum, #shifts, or #penalties), 
                                and y_bad is a bad enough small score
            assume the function f takes the format `y = base^{-(x-min_value)}`
            then we just need to solve the equation `y_bad = base^{-(x_bad-min_value)}`
            solving for base, we get `base = math.pow(1/y_bad, 1 / (x_bad - min_value))`
            then we can get the return value by plugging in shifts to `y = base^{-(x-min_value)}`        
        Now we can precisely control the behavior of the scoring function!! That is, 
        if a scoring func is made with `scoring_func = function_factory(min_value, x_bad, y_bad)`, 
        then it's guaranteed that 
            scoring_func(min_value) = 1
            scoring_func(x_bad) = y_bad
            and scoring_func(x) always > 0 (because it's an exponential function)
        """
        if monoDecr: 
            # format: y = base^{anchor-x}
            base = math.pow(y_bad, 1 / (anchor - x_bad))
            def scoring_func(x_input): 
                return math.pow(base, anchor - x_input)
            return scoring_func
        else: 
            # format: y = base^{x-anchor}
            base = math.pow(y_bad, 1 / (x_bad - anchor))
            def scoring_func(x_input): 
                return math.pow(base, x_input - anchor)
            return scoring_func            

    def compute_distance_score(self):
        # end_distance_sum = self.ingredients[END_DISTANCE_SUM]
        # init_distance_sum = self.ingredients[INIT_DISTANCE_SUM]
        # expected_distance_sum = self.ingredients[EXPECTED_DISTANCE_SUM]

        # if end_distance_sum > expected_distance_sum: 
        #     # worse than random, absolutely bad, # distance_score is 0
        #     # game is lost, bench_score is 0
        #     return 0

        # # expected_distance_score = max(0, 1 - end_distance_sum / expected_distance_sum)
        # # distance_reduction_score = max(0, 1 - end_distance_sum / init_distance_sum)

        # # return (expected_distance_score + distance_reduction_score) / 2
        # expected_distance_score = max(0, 1 - end_distance_sum / expected_distance_sum)
        # return expected_distance_score        
        end_distance_sum = self.ingredients[END_DISTANCE_SUM]

        if self.distance_score_func is None: 
            expected_distance_sum = self.ingredients[EXPECTED_DISTANCE_SUM]
            x_bad = expected_distance_sum
            y_bad = 0.1 # an arbitrary number
            self.distance_score_func = MetricCalculator.function_factory(0, x_bad, y_bad)

        # now we have a softer score when end_distance_sum > expected_distance_sum,
        # it's a small number rather than a hard line 0
        return self.distance_score_func(end_distance_sum)

    def compute_consistency_score(self):
        # max_shifts = self.ingredients[MAX_SHIFTS]
        # min_shifts = self.ingredients[MIN_SHIFTS]
        # shifts = self.ingredients[SHIFTS]

        # # when the players don't cover all the icons, return the best score 1
        # # we will capture this error with another metric, Coverage Score
        # if shifts < min_shifts: 
        #     return 1

        # # add-one smoothing
        # normalized = (shifts - min_shifts) / (max_shifts + 1 - min_shifts)
        # return 1 - normalized
        min_shifts = self.ingredients[MIN_SHIFTS]
        shifts = self.ingredients[SHIFTS]

        # in this case consistency score doesn't make sense
        # and will be taken out of bench_score
        if shifts < min_shifts: 
            return None

        if self.consistency_score_func is None: 
            bad_enough_shifts = min_shifts * 2 # min_shifts * k, actually, k might need to be a function of #objects, too
            bad_enough_score = 0.1
            self.consistency_score_func = MetricCalculator.function_factory(min_shifts, bad_enough_shifts, bad_enough_score)
        
        return self.consistency_score_func(shifts)

    def compute_penalty_score(self):     
        # penalties = self.ingredients[PENALTIES]
        # max_penalties = self.ingredients[MAX_PENALTIES]
        # normalized = penalties / max_penalties
        # return 1 - normalized  # we can use different function at this step
        penalties = self.ingredients[PENALTIES]
        max_penalties = self.ingredients[MAX_PENALTIES]

        if self.penalty_score_func is None: 
            bad_enough_penalties = max_penalties # this should probably also be a function of #objects
            bad_enough_score = 0.05
            self.penalty_score_func = MetricCalculator.function_factory(0, bad_enough_penalties, bad_enough_score)        

        return self.penalty_score_func(penalties)
    
    
    def compute_coverage_score(self):
        id_set = set([ele['freepik_id'] for ele in self.ingredients[INIT_STATES]['state1']])
        moves: List[Tuple[str, PositionedIcon]] = self.ingredients[MOVES]
        players = self.ingredients[PLAYERS]

        moved_obj_per_player = [set() for _ in players]
        
        for move in moves: 
            idx = players.index(move[0])
            moved_obj_per_player[idx].add(move[1]['freepik_id'])

        # # add-one smoothing to avoid return 0
        # coverage_per_player = [(len(moved_obj_set) + 1) / (len(id_set) + 1) for moved_obj_set in moved_obj_per_player]
        # # return product(% of icons moved by each player)
        # return math.prod(coverage_per_player) # we can also plug it in a monotonously increasing function on (0, 1]
        coverage_per_player = [len(moved_obj_set) / len(id_set) for moved_obj_set in moved_obj_per_player]
        mean_coverage = sum(coverage_per_player) / len(coverage_per_player)

        if self.coverage_score_func is None: 
            worst_coverage = 0
            worst_coverage_score = 0.01
            self.coverage_score_func = MetricCalculator.function_factory(1, worst_coverage, worst_coverage_score, monoDecr=False)        

        return self.coverage_score_func(mean_coverage)

    def compute_metrics(self): 
        sub_metrics = {name: func() for name, func in self.sub_metric_funcs.items()}

        for key in sub_metrics_registry:
            if key not in sub_metrics:
                raise ValueError(f"MetricCalculator: Key '{key}' is not in the sub-metrics registry.")
        
        if self.ingredients[SHIFTS] < self.ingredients[MIN_SHIFTS]: 
            # in this case, consistency score doesn't make sense,
            # rm consistency score to prevent it artificially drives up the bench_score
            del sub_metrics[CONSISTENCY_SCORE]

        # Take the harmonic mean of the sub-metrics
        bench_score = harmonic_mean(sub_metrics.values()) 

        # overwrite MAX_SHIFT for existing interactions.json file
        self.ingredients[MAX_SHIFTS] = self.ingredients[MIN_SHIFTS] * 2         

        return sub_metrics, bench_score, self.ingredients