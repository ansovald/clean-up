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
    {'dim': 9, 'branches': 7, 'empty_cells': 34, 'difficulty': 'easy'},
    {'dim': 9, 'branches': 11, 'empty_cells': 29, 'difficulty': 'medium'},
    {'dim': 9, 'branches': 15, 'empty_cells': 24, 'difficulty': 'hard'}
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
            print(f"Generated {len(grids)} grids for {id_string}")
            empty_cell_counts = []
            for grid in grids:
                empty_cells = sum(row.count(EMPTY_SYMBOL) for row in grids[grid])
                empty_cell_counts.append(empty_cells)

            with open(id_string + '_exhaustive.json', 'w', encoding='utf-8') as f:
                json.dump(grids, f, ensure_ascii=False, indent=4)

def sample_exhaustive_files(n_samples=10000):
    """
    Samples from the exhaustive grid files and returns a grids.json file with the sampled grids.
    """
    info_text = f"For each difficulty level, max. {n_samples} grids have been samples from the exhaustive files enumerating all grids with the respective specifications"
    sampled_grids = {
        "info": {
            "text": info_text,
        }
    }
    for config in GRID_CONFIGS:
        id_string = f"{config['dim']}x{config['dim']}_e{config['empty_cells']}_b{config['branches']}"
        total_cells = (config['dim']-2) * (config['dim']-2)
        empty_cell_ratio = config['empty_cells'] / total_cells
        branch_count = config['branches']
        sampled_grids["info"][id_string] = {
            "difficulty": config['difficulty'],
            "dim": config['dim'],
            "empty_cells": config['empty_cells'],
            "total_cells": total_cells,
            "empty_cell_ratio": empty_cell_ratio,
            "branch_count": branch_count,
        }
        with open(id_string + '_exhaustive.json', 'r', encoding='utf-8') as f:
            grids = json.load(f)
            sampled_grids["info"][id_string]['total_model_count'] = len(grids)
            sampled_keys = random.sample(list(grids.keys()), min(n_samples, len(grids)))
            sampled_grids[id_string] = {}
            for key in sampled_keys:
                sampled_grids[id_string][key] = grids[key]

    with open('grids.json', 'w', encoding='utf-8') as f:
        json.dump(sampled_grids, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    # generate_all_grids(grid_configs=GRID_CONFIGS, models=5000000)
    sample_exhaustive_files(n_samples=10000)
    