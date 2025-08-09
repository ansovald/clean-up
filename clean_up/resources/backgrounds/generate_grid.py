from clingo.control import Control
from random import randint
import json
import random
import os

from numpy import empty
EMPTY_SYMBOL = "◌"

frame_dict = {
    "┌": "╔",
    "┐": "╗",
    "└": "╚",
    "┘": "╝",
    "├": "╟",
    "┤": "╢",
    "┬": "╤",
    "┴": "╧",
    "─": "═",
    "│": "║"
}    

# used for debugging asp encoding
# def find_attribute(model, attribute="r_count"):
#     pattern = r'r_count\([^)]+\)'
#     matches = re.findall(pattern, model)
#     matches = [match.strip() for match in matches]
#     for match in matches:
#         print(match)

def parse_model(model, width, height):
        """
        Parses the ASP model and returns a string representation of the grid.
        """
        model = str(model)
        model = model.split(" ")
        # Initalize grid as list of height empty lists, each representing a row
        grid = [[EMPTY_SYMBOL for _ in range(width)] for _ in range(height)]
        for atom in model:
            if atom.startswith("cell("):
                if atom.endswith(")."):
                    atom = atom[5:-2]
                else:
                    atom = atom[5:-1]
                # print(atom)
                x, y, value = atom.split(',')
                x = int(x)
                y = int(y)
                value = value[1]
                grid[y][x] = value
                if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                    grid[y][x] = frame_dict[grid[y][x][0]]
        return "\n".join("".join(row) for row in grid)

GRID_CONFIGS = [
    {'dim': 9, 'branches': 7, 'empty_cells': 34},
    {'dim': 9, 'branches': 11, 'empty_cells': 29},
    {'dim': 9, 'branches': 15, 'empty_cells': 24}
]

def generate_all_grids(grid_configs=GRID_CONFIGS, models=1000, encoding='grid_encoding.lp'):
    for config in grid_configs:
        dim = config['dim']
        branches = config['branches']
        empty_cells = config['empty_cells']
        id_string = f'{dim}x{dim}_e{empty_cells}_b{branches}'
        # load ASP encoding:
        with open(encoding, 'r', encoding='utf-8') as lp_file:
            grid_lp = lp_file.read()

        # init clingo controller with maximum args.models answer sets
        ctl = Control([f"{models}"])

        grid_lp += f"\ngrid_size({dim-1},{dim}-1)."
        grid_lp += f'\n:- {branches} != #count {{ X,Y,F : cell(X,Y,F), branch(F) }}.'
        grid_lp += f'\n:- {empty_cells} != #count {{ X,Y,F : cell(X,Y,F), empty(F) }}.'
        
        # add encoding to clingo controller:
        ctl.add(grid_lp)
        # ground the encoding:
        ctl.ground()
        grids = {}
        # solve encoding, collect produced models:
        with ctl.solve(yield_=True) as solve:
            print(f'\tEncoding is {str(solve.get()).lower()}isfiable')
            for i, model in enumerate(solve):
                grids[i] = parse_model(model=model, width=dim, height=dim)
        if len(grids) > 0:
            empty_cell_counts = []
            for grid in grids:
                empty_cells = sum(row.count(EMPTY_SYMBOL) for row in grids[grid])
                empty_cell_counts.append(empty_cells)

            with open(id_string + '.json', 'w', encoding='utf-8') as f:
                json.dump(grids, f, ensure_ascii=False, indent=4)

def sample_exhaustive_files(n_samples=10000):
    """
    Samples from the exhaustive grid files and returns a grids.json file with the sampled grids.
    """
    # Find exhaustive grid files, ending with `_exhaustive.json`
    exhaustive_files = [f for f in os.listdir('.') if f.endswith('_exhaustive.json')]
    sampled_grids = {
        "info": {
            "text": "For each difficulty level, 10.000 grids have been samples from the exhaustive files enumerating all grids with the respective specifications",
            "easy": {
                "id_string": "9x9_e34_b7",
                "dim": 9,
                "empty_cells": 34,
                "total_cells": 49,
                "empty_cell_ratio": 0.6938775510204082,
                "branch_count": 7,
                "model_count": 63859
            },
            "medium": {
                "id_string": "9x9_e29_b11",
                "dim": 9,
                "empty_cells": 29,
                "total_cells": 49,
                "empty_cell_ratio": 0.5918367346938775,
                "branch_count": 11,
                "model_count": 1222435
            },
            "hard": {
                "id_string": "9x9_e24_b15",
                "dim": 9,
                "empty_cells": 24,
                "total_cells": 49,
                "empty_cell_ratio": 0.4897959183673469,
                "branch_count": 15,
                "model_count": 2696476
            }
        }
    }
    for file in exhaustive_files:
        with open(file, 'r', encoding='utf-8') as f:
            id_string = file.split('_exhaustive.json')[0]
            grids = json.load(f)
            sampled_keys = random.sample(list(grids.keys()), min(n_samples, len(grids)))
            sampled_grids[id_string] = {}
            for key in sampled_keys:
                sampled_grids[id_string][key] = grids[key]['grid']
    with open('grids.json', 'w', encoding='utf-8') as f:
        json.dump(sampled_grids, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    # generate_all_grids(grid_configs=GRID_CONFIGS, models=10000, encoding='grid_encoding.lp')
    sample_exhaustive_files(n_samples=10000)
    