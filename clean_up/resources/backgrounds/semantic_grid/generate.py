"""
Generate models under 3 configurations with clingo, and save to json files.
The generation is done in batches, each batch is enforced with a few random empty cells, 
which adds to randomness of the first `BATCH_SIZE` models showing up. 
Models within the same batch have minor differences, e.g., they differ by just one cell; 
models across batches have more variances. 

Usage: 
At game root directory (clean-up/clean_up), run the following command: 
```
python -m resources.backgrounds.semantic_grid.generate
```
The result json files will be saved in the same directory as this file.
"""
import clingo
import random 
import json
import time 
from functools import wraps
import sys
import os

TOTAL_MODELS = 5000 # models per configuration
BATCH_SIZE = 50     # models per batch
N_COLS = 50
N_ROWS = 10

"""
On top of the predicates in `kitchen.lp` and `shapes.lp`, 
there are 3 configurations, each for one difficulty level (easy/medium/hard);
each configuration adds a set of atoms to control the generation.
Each configuration is defined by:

atoms: 
    `occupied_ratio(O)`: percentage of occupied cells (0-100)
    `h_padding(P)`: horizontal padding on left and right(0-2 columns on each side)
    `v_padding(P)`: vertical padding on top and bottom (0-1 rows on each edge)
    `left_gutter(B)`: left gutter of each placement (true/false)
    `right_gutter(B)`: right gutter of each placement (true/false)
    `lr_proportional_gutter(B)`: left/right gutter proportional to block span of the shape of the placement (true/false)
    `bottom_gutter(B)`: bottom gutter of each placement (true/false)
n_empty: 
    number of empty cells to randomly select for each attempt
timeout:
    maximum time (in seconds) to wait for each batch of solutions
"""
CONFIGS = {
    # "config_75": {
    #     "atoms": """occupied_ratio(75).
    #                 h_padding(0).
    #                 v_padding(0).
    #                 left_gutter(false).
    #                 right_gutter(false).
    #                 lr_proportional_gutter(false).
    #                 bottom_gutter(false).
    #                 """, 
    #     "n_empty": 2,     # number of enforced empty cells
    #     "timeout": 99     # allow 99 seconds for each batch
    # },
    "config_70": {
        "atoms": """occupied_ratio(70).
                    h_padding(0).
                    v_padding(0).
                    left_gutter(false).
                    right_gutter(false).
                    lr_proportional_gutter(false).
                    bottom_gutter(false).
                    """, 
        "n_empty": 2,     # number of enforced empty cells
        "timeout": 99     # allow 99 seconds for each batch
    },
    "config_50": {
        "atoms": """occupied_ratio(50).
                    h_padding(2).
                    v_padding(1).
                    left_gutter(true).
                    right_gutter(true).
                    lr_proportional_gutter(false).
                    bottom_gutter(false).
                    """, 
        "n_empty": 3, 
        "timeout": 66
    },
    "config_35": {
        "atoms": """occupied_ratio(35).
                    h_padding(2).
                    v_padding(1).
                    left_gutter(true).
                    right_gutter(true).
                    lr_proportional_gutter(true).
                    bottom_gutter(true).
                    """, 
        "n_empty": 5,  
        "timeout": 33
    }
}


def timer(format_func=lambda elapsed, *args, **kwargs: f"\tElapsed: {elapsed:.4f} seconds"):
    """
    A decorator to time a function and print the elapsed time using a custom format function.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            print(format_func(end-start, *args, **kwargs))
            return result
        return wrapper
    return decorator


@timer()
def compute_batch(ctl, empty_coords, timeout): 
    """
    Solve for a batch of models with timeout. 
    :param ctl: clingo.Control object
    :param empty_coords: list of tuples (x,y) of randomly selected empty cells
    :param timeout: maximum time (in seconds) to wait for solutions
    :return: list of models (as strings of predicates) of the batch
    """
    ctl.configuration.solve.models = BATCH_SIZE
    models = []

    def on_model(model):
        # Save only shown symbols
        models.append(' '.join([str(sym) for sym in model.symbols(shown=True)]))

    assumptions = [(clingo.Function("empty_cell", [clingo.Number(i),clingo.Number(j)]), True) for (i,j) in empty_coords]

    with ctl.solve(assumptions=assumptions, on_model=on_model, async_=True) as handle:
        if not handle.wait(timeout):
            handle.cancel()   # safe cancel, release memory if timeout
        handle.get()          # get the models even if not reaching BATCH_SIZE

    return models


def compute_models(config_key): 
    """
    Compute TOTAL_MODELS models for the configuration associated with `config_key`.
    It uses the same clingo.Control object for each config, but solve 
    with different assumptions of empty cells per batch. 
    :param config_key: key in CONFIGS
    :return: list of all models (as strings) for the configuration
    """
    all_models = []
    attempt = 0

    config_body = CONFIGS[config_key]
    atoms = config_body["atoms"]
    n_empty = config_body["n_empty"]
    timeout = config_body["timeout"]

    ctl = clingo.Control(["-c", f"width={N_COLS}", 
                            "-c", f"height={N_ROWS}", 
                            "-c", "jitter=2"]
                            , logger=lambda code, msg: None  # suppress clingo warnings
                        )  

    ctl.load(os.path.join("resources", "backgrounds", "semantic_grid", "kitchen.lp"))
    ctl.load(os.path.join("resources", "backgrounds", "semantic_grid", "shapes.lp"))
    ctl.add("config", [], atoms)

    ctl.ground([("config", [])])   # the config atoms section
    ctl.ground([("base", [])])     # kitchen.lp and shapes.lp 

    while len(all_models) < TOTAL_MODELS:
        attempt += 1
        
        # assumption: empty cells
        empty_x = random.sample(range(1, N_COLS+1), n_empty)  
        empty_y = random.sample(range(1, N_ROWS+1), n_empty)
        empty_coords = list(zip(empty_x, empty_y))            

        empty_coords_str = ""
        for x,y in empty_coords: 
            empty_coords_str += f"empty_cell({x},{y}). "
        print(f"{config_key}-{attempt}: solving with these empty cells:\n\t{empty_coords_str}")

        batch = compute_batch(ctl, empty_coords, timeout)

        for m in batch: 
            all_models.append({
                "config": config_key,
                "attempt": attempt,
                "empty_cells": empty_coords_str,
                "model": m
            })
        print(f"Total models: {len(all_models)}\n")
    
    return all_models


class Logger:
    """
    A class to duplicate stdout to both console and a file.
    """
    def __init__(self, filename):
        self.file = open(filename, "a")
        self.stdout = sys.stdout  

    def write(self, data):
        self.stdout.write(data)
        self.file.write(data)

    def flush(self):  
        self.stdout.flush()
        self.file.flush()

if __name__ == "__main__":
    sys.stdout = Logger("log.txt")

    for config_key in CONFIGS: 
        start = time.time()
        all_models = compute_models(config_key)
        end = time.time()
    
        print("=======================================================")
        print(f"{config_key} total time: {(end-start):.4f} seconds")
        print("=======================================================")
        
        with open(f"{config_key}.json", "w") as f:
            json.dump(all_models, f, indent=4)            


