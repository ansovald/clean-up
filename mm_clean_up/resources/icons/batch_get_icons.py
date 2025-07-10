import os
import subprocess

"""
This script is just a wrapper of `get_icons.py`,
it gets the info of icons in batch. 
see `get_icons.py` for the detailed reasons.

----- SCRIPT USAGE -----
Update `terms` with the desired search terms. 

Run this in "resource/icon" directory to save icons to the correct path:
```
API_KEY=<Freepik_API_key> python batch_get_icons.py
```
"""

API_KEY = os.getenv("API_KEY")

terms = [
        # ---------- 13 utensils & tableware & cookware ----------
        # "bowl",
        # "coffee mug",
        # "fork",
        # "plate",
        # "pot",
        # "wine bottle",
        # "napkin",          # no icons in any color
        # "spoon",           # no icons in any color
        # "whisk",           # no icons in any color
        # "kitchen knife",   # no icons in any color
        # "peeler",          # no icons in any color
        # "frying pan",      # no icons in any color
        # "cutting board",   # no icons in any color
        # ---------- 16 fruits and vegetables ----------
        # "apple",
        # "banana",          # no icons in any color
        # "orange",          # no icons in any color
        # "grape",           # no icons in any color
        # "strawberry",      # no icons in any color
        # "watermelon",      # no icons in any color
        # "peach",           # no icons in any color
        # "pear",            # no icons in any color
        # "pineapple",       # no icons in any color
        # "carrot",          # no icons in any color
        # "broccoli",        # no icons in any color
        # "tomato",          # no icons in any color
        # "cucumber",        # no icons in any color
        # "onion",           # no icons in any color
        # "garlic",          # no icons in any color
        # "potato",          # no icons in any color
        # ---------- 11 sweets and snacks ----------
        # "ice cream", 
        # "burger",
        # "cake",
        # "chocolate",       
        # "sushi",           # no icons in any color
        # "hotdog",          # no icons in any color
        # "noodle",          # no icons in any color
        # "steak",           # no icons in any color
        # "omelette",        # no icons in any color
        # "salad",           # no icons in any color
        # "pancake",         # no icons in any color
        # "taco",            # no icons in any color
        # "pizza",           # no icons in any color
        # "hot dog",         # no icons in any color
        # "french fries",    # no icons in any color
        # "soda",            # no icons in any color
        # "sandwich",        # no icons in any color
        # "donut",           # no icons in any color
        # "cookie",          # no icons in any color
        # "muffin",          # no icons in any color
        # ----------many household items ----------
        # "coin",
        # "camera",
        # "shopping bag",
        # "plant pot",
        # "watch",
        # "battery",
        # "bookmark",
        # "hat",
        # "hammer",
        # "ruler",
        # "helmet",
        # "mask",
        # "headphones",
        # "cable",
        # "speaker", 
        # "alarm clock", 
        # "laptop",
        # "smartphone",
        # "light bulb",
        # "glove",
        # "bucket",
        # "soap",
        # "brush",
        # "tape",
        # "candle",
        # "pencil",
        # "pen",
        # "notebook",
        # "wallet",
        # "key",
        # "backpack",
        # "remote control",
        # "game controller",
        # "keyboard",
        # "water bottle",
        # "umbrella",
        # "mirror",
        # "shoe",
        # "calculator",
        # "ID card",
        # "credit card",
        # "lock",
        # "car key",         # no icons in any color
        # "lighter",         # no icons in any color
        # "water jug",       # no icons in any color
        # "magnet",          # no icons in any color
        # "phone case",      # no icons in any color
        # "mousepad",        # no icons in any color
        # "tripod",          # no icons in any color
        # "SIM card",        # no icons in any color
        # "passport",        # no icons in any color
        # "USB stick",       # no icons in any color
        # "photo frame",     # no icons in any color
        # "scarf",           # no icons in any color
        # "coat",            # no icons in any color
        # "candleholder",    # no icons in any color
        # "eraser",          # no icons in any color
        # "tissue box",      # no icons in any color        
        # "boot",            # no icons in any color
        # "screwdriver",     # no icons in any color
        # "nail",            # no icons in any color
        # "stapler",         # no icons in any color
        # "flashlight",      # no icons in any color
        # "lunch tray",      # no icons in any color
        # "charger",         # no icons in any color
        # "hairbrush",       # no icons in any color
        # "shampoo",         # no icons in any color
        # "broom",           # no icons in any color
        # "vacuum cleaner",  # no icons in any color
        # "mop",             # no icons in any color
        # "scissors",        # no icons in any color
        # "teacup",          # no icons in any color
        # "lunchbox",        # no icons in any color
        # "toilet paper",    # no icons in any color
        # "blender",         # no icons in any color
        # "electric kettle", # no icons in any color
        # "hairdryer",       # no icons in any color
        # "toaster",         # no icons in any color
        # "sunglasses",      # no icons in any color
        # "sponge",          # no icons in any color
        # "spray bottle",    # no icons in any color
        # "dish",            # no icons in any color
        # "towel",           # no icons in any color
        # "toothbrush",      # no icons in any color
        # "toothpaste",      # no icons in any color
        # "razor",           # no icons in any color
        # "comb",            # no icons in any color
]

for term in terms:
    env = os.environ.copy()
    env["API_KEY"] = API_KEY
    subprocess.run(["python", "get_icons.py", term], env=env)
