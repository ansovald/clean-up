from clingo.control import Control
from random import randint
from game_grid import GameGrid

EMPTY_SYMB = "◌"

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
        grid = [[EMPTY_SYMB for _ in range(width)] for _ in range(height)]
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
        # parsed_grid = []
        # for row in grid:
        #     parsed_grid.append("".join(row))
        return "\n".join("".join(row) for row in grid)

def generate_grid(encoding: str='grid_encoding.lp', models: int=1000, grid_size: tuple[int, int]=(8, 12), branches: int=None, save_file: bool=False, display: int=None):
    """
    Generates a grid based on the provided parameters.
    :param model: Number of models to generate
    :param grid_size: Size of the grid (width, height)
    :param neighbors: Minimum and maximum number of empty neighbors any empty cell must have
    :param single: Enforce number of empty cells without neighbors
    :param corners: Limit number of corner tiles
    :param branches: Limit number of branch tiles
    :param corner_branches_per_row: Limit number of corners/branches per row
    :param corner_branches_per_column: Limit number of corners/branches per column
    :param display: Number of random grids to display
    :return: Name of the generated JSON file containing the grids
    """
    # load ASP encoding:
    with open(encoding, 'r', encoding='utf-8') as lp_file:
        grid_lp = lp_file.read()

    # init clingo controller with maximum args.models answer sets
    ctl = Control([f"{models}"])

    grid_lp += f"\ngrid_size({grid_size[0]-1},{grid_size[1]}-1)."
    if branches:
        grid_lp += f'\n:- {branches} != #count {{ X,Y,F : cell(X,Y,F), branch(F) }}.'

    # add encoding to clingo controller:
    ctl.add(grid_lp)
    # ground the encoding:
    ctl.ground()
    # report successful grounding:
    print("Grounded!")
    # solve encoding, collect produced models:
    grids = { }
    with ctl.solve(yield_=True) as solve:
        print(f'Encoding is {str(solve.get()).lower()}isfiable')
        for i, model in enumerate(solve):
            grids[i] = parse_model(model=model, width=grid_size[0], height=grid_size[1])

    if display > models:
        display = models

    if display:
        if len(grids) > 0:
            rand_array = [randint(0,len(grids)-1) for _ in range(display)]
            for i in rand_array:
                print(f'grid {i}:')
                grid = GameGrid(grids[i])
                print(grid.__str__(show_coords=True))
                # count the number of empty cells in the grid
                empty_cells = sum(row.count(EMPTY_SYMB) for row in grids[i])
                print(f'Number of empty cells: {empty_cells}')                                  

    id_string = f'gs{grid_size[0]}x{grid_size[1]}'
    if branches:
        id_string += f'_b{branches}'

    if save_file:
        import json
        with open(f'{id_string}.json', 'w', encoding='utf-8') as f:
            json.dump(grids, f, ensure_ascii=False, indent=4)

    return f'{id_string}.json'

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate grids from ASP encoding.")
    parser.add_argument("-e", "--encoding", type=str, default="grid_encoding.lp", help="Path to the ASP encoding file")
    parser.add_argument("-m", "--models", type=int, default=1000, help="Number of models to generate")
    parser.add_argument("-d", "--display", type=int, default=20, help="Number of random grids to display")
    parser.add_argument("-gs", "--grid_size", type=int, nargs=2, default=[21,9], help="Width and height of the grid, default is 21, 9")
    parser.add_argument("-b", "--branches", type=int, default=None, help="Limit number of branch tiles (\"├\";\"┤\";\"┬\";\"┴\";\"┼\"), e.g. to 14")
    parser.add_argument("-s", "--save", help="Save the generated grids to a file", action='store_true')
    args = parser.parse_args()
    print(args)

    generate_grid(
        models=args.models,
        grid_size=tuple(args.grid_size),
        branches=args.branches,
        save_file=args.save,
        display=args.display
    )

if __name__ == "__main__":
    main()
    