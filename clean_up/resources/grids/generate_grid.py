from clingo.control import Control
from random import randint

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

def generate_grid(encoding: str='grid_encoding.lp', models: int=1000, grid_size: tuple[int, int]=(8, 12), neighbors: tuple[int,int]=None, single: int=None,
                  corners: int=None, branches: int=None, corner_branches_per_row: int=None,
                  corner_branches_per_column: int=None, display: int=None):
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
    if neighbors and neighbors[0] is not None and neighbors[1] is not None:
        # slot must have at least 1 neighbouring slot, and 5 at maximum
        grid_lp += f'\n:- cell(X,Y,F), grid_size(W,H), 0 < X < W, 0 < Y < H, not {neighbors[0]} <= #count {{ XA,YA : cell(XA, YA, "◌"), XA=X-1..X+1, YA=Y-1..Y+1 }} < {neighbors[1]}.'

    if single:
        # set the number of single slot compartments
        grid_lp += "\nsingle(X,Y) :- cell(X,Y,F), grid_size(W,H), 0 < X < W, 0 < Y < H, 1 = #count { XA,YA : cell(XA, YA, \"◌\"), XA=X-1..X+1, YA=Y-1..Y+1 }."
        grid_lp += f'\n:- not {single} = #count {{ X,Y : single(X,Y) }}.'
    # Limit the number of possible corners and branches, respectively
    if corners:
        grid_lp += f'\n:- {corners} < #count {{ X,Y,F : cell(X,Y,F), corner(F) }}.'
    if branches:
        grid_lp += f'\n:- {branches} != #count {{ X,Y,F : cell(X,Y,F), branch(F) }}.'
    # limit number of corners+branches in each row and column, e.g. 8 and 4
    if corner_branches_per_row:
        grid_lp += f'\n:- Y=0..H, grid_size(_,H), CC = #count {{ X,F : cell(X,Y,F), corner(F) }}, BC = #count {{ X,F : cell(X,Y,F), branch(F) }}, not CC+BC < {corner_branches_per_row}.'
    if corner_branches_per_column:
        grid_lp += f'\n:- X=0..W, grid_size(W,_), CC = #count {{ Y,F : cell(X,Y,F), corner(F) }}, BC = #count {{ Y,F : cell(X,Y,F), branch(F) }}, not CC+BC < {corner_branches_per_column}.'

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
                print(grids[i])
                # count the number of empty cells in the grid
                empty_cells = sum(row.count(EMPTY_SYMB) for row in grids[i])
                print(f'Number of empty cells: {empty_cells}')                                  

    id_string = f'gs{grid_size[0]}x{grid_size[1]}'
    if neighbors[0]:
        id_string += f'_n{neighbors[0]}-{neighbors[1]}'
    if single:
        id_string += f'_s{single}'
    if corners:
        id_string += f'_c{corners}'
    if branches:
        id_string += f'_b{branches}'
    if corner_branches_per_row:
        id_string += f'_cbr{corner_branches_per_row}'
    if corner_branches_per_column:
        id_string += f'_cbc{corner_branches_per_column}'

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
    parser.add_argument("-n", "--neighbors", type=int, nargs=2, default=[None, None], help="Min and max number of empty neighbors any empty cell must have")
    parser.add_argument("-s", "--single", type=int, default=None, help="Enforce number of empty cells without neighbors")
    parser.add_argument("-c", "--corners", type=int, default=None, help="Limit number of corner tiles (\"┌\";\"┐\";\"└\";\"┘\"), e.g. to 12")
    parser.add_argument("-b", "--branches", type=int, default=None, help="Limit number of branch tiles (\"├\";\"┤\";\"┬\";\"┴\";\"┼\"), e.g. to 14")
    parser.add_argument("-cbr", "--corner_branches_per_row", type=int, default=None, help="Limit number of corners/branches per row, e.g. to 8")
    parser.add_argument("-cbc", "--corner_branches_per_column", type=int, default=None, help="Limit number of corners/branches per column, e.g. to 4")
    args = parser.parse_args()

    generate_grid(
        models=args.models,
        grid_size=tuple(args.grid_size),
        neighbors=tuple(args.neighbors),
        single=args.single,
        corners=args.corners,
        branches=args.branches,
        corner_branches_per_row=args.corner_branches_per_row,
        corner_branches_per_column=args.corner_branches_per_column,
        display=args.display
    )

if __name__ == "__main__":
    main()
    