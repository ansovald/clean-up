"""
Wrangle the models in json files, into a format suitable for instancegenerator.py.

Usage: 
At game root directory (clean-up/clean_up), run the following command: 
```
python -m resources.backgrounds.semantic_grid.data_wrangling
```
The result will be saved in `resources/backgrounds/semantic_grids.json`.
"""
import os
import re
import random
import json
from .generate import N_ROWS, N_COLS, CONFIGS
from resources.game_state.utils import EMPTY_SYMBOL


PATTERN = r"cover\((?P<X>\d+),\s*(?P<Y>\d+),\s*(?P<OID>[\w-]+),\s*(?P<PPID>\d+)\)"

# mapping span/oid to a list of possible Objects
# for object with span S, symbol should repeat S-2 times (excluding the brackets)
# and there are two options of symbols for each span
symbols =  ['♠', '♣', '♥', '♦', '▲', '●', '■', '☾', '★', '⚑']
spans = [5, 6, 7, 8, 9]  # this is determined in ASP encoding, see `kitchen.lp` and `shapes.lp`

OBJ_REGISTRY = {}

for s in spans: 
    i = (s - 5) * 2
    length = s - 2
    OBJ_REGISTRY[s] = [symbols[i]*length, symbols[i+1]*length] 


def get_grid_display(model_string, showObject=True, showCoordinates=False, indexWidth=3): 
    """
    Transform the list format of a grid into a string, 
    adding the surrounding boundaries and the coordinate system. 
    :param model_string: a big string representing an ASP model
    :param showObject: if True, print readable objects; else print ObjectID
    """
    grid_list = get_grid_list(model_string, showObject=showObject)
    n_cols = len(grid_list[0])
    top = f"╔{'═'*(N_COLS)}╗"
    inners = [f"║{''.join(inn)}║" for inn in grid_list]
    bot = f"╚{'═'*(N_COLS)}╝"
    if showCoordinates: 
        p = indexWidth
        top = f"{get_y_coord(p, None)}{top}"
        inners = [f"{get_y_coord(p, idx)}{inner}" for idx, inner in enumerate(inners)]
        bot = f"{get_y_coord(p, None)}{bot}"
        x_coords = f"{get_y_coord(p+1, None)}{get_x_coords(N_COLS)}"

    parts = [top, *inners, bot]
    if showCoordinates:
        parts.append(x_coords)

    return "\n".join(parts)


def get_grid_list(model_string, showObject=True): 
    """
    Transform an ASP model into a nested list that represents a grid. 
    :param model_string: a big string representing an ASP model
    """
    # res:     
    # {
    #     ppid: [[(x,y)], oid, obj]
    # }
    res = {}
    for m in re.finditer(PATTERN, model_string): 
        x = int(m.group('X'))
        y = int(m.group('Y'))
        oid = int(m.group('OID'))
        ppid = m.group('PPID')
        if not ppid in res:
            obj = random.choice(OBJ_REGISTRY[oid])
            res[ppid] = [[(x, y)], int(oid), obj]
        else: 
            res[ppid][0].append((x, y))
    
    # sanity check: number of cells in a placement should be a multiple of horizontal span of an object block
    for key, val in res.items(): 
        assert len(val[0]) % (int(val[1])) == 0
        
    grid_list = [[EMPTY_SYMBOL for j in range(N_COLS) ] for i in range(N_ROWS)]
    
    for ppid, val in res.items(): 
        obj_block = f"[{val[2]}]"
        obj_block_len = len(obj_block)
        coords = sorted(val[0], key=lambda coord: (coord[1], coord[0]))
        for i in range(len(coords)): 
            x,y = coords[i]
            content = obj_block[i % obj_block_len] if showObject else str(val[1])
            grid_list[y-1][x-1] = content
    
    return grid_list 
    

def get_y_coord(padding_width, y_index) -> str: 
    if y_index is None:
        return " " * padding_width
    return f"{y_index:^{padding_width}}"
    
def get_x_coords(n_cols, tick_block=5):
    """
    Convert numbers 1 to n_cols into x-coordinate, only show every tick_block-th number. 
    """
    return ''.join([str(tick).ljust(tick_block) for tick in range(0, n_cols, tick_block)])

def clean_configs(configs): 
    cleaned = {}
    for k, v in configs.items(): 
        cleaned[k] = {}
        for inner_k, inner_v in configs[k].items(): 
            if inner_k == 'atoms': 
                cleaned[k]['atoms'] = re.sub(r"\s+", " ", inner_v).strip()
            else: 
                cleaned[k][inner_k] = inner_v
    return cleaned
    

if __name__ == "__main__": 
    base = "resources/backgrounds/semantic_grid/"
    filenames = ['config_35.json', 'config_50.json', 'config_70.json']
    paths = [os.path.join(base, fn) for fn in filenames]
    all_data = [json.load(open(p)) for p in paths]   

    instances = {}
    instances['info'] = clean_configs(CONFIGS)

    for data in all_data: 
        config_name = data[0]['config'] 
        instances[config_name] = { idx: get_grid_display(ele['model']) for idx, ele in enumerate(data) }


    with open(os.path.join("resources/backgrounds/", "semantic_grids.json"), "w", encoding="utf-8") as f:
        json.dump(instances, f, ensure_ascii=False, indent=4)     
