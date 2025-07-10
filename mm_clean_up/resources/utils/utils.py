import json
import os
from typing import List
from .types import Icon

def load_or_create_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
    else:
        data = {}

    return data

def save_json(data, filepath):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

"""
Update the <NOUN>-<COLOR> list.
{
    "<NOUN>": {
        "<COLOR>": [
            {
                "freepik_id": 253176,
                "name": "fork",
                "url": "https://cdn-icons-png.freepik.com/128/253/253176.png"
            },
            // ...
        ], 
        // ...
    },
    // ... 
}
"""
def update_metadata(filepath, noun: str, color: str, new_items: List[Icon]):
    data = load_or_create_json(filepath)

    # Ensure parent_key exists and is a dict
    if noun not in data or not isinstance(data[noun], dict):
        data[noun] = {}

    # Update nested dict
    data[noun].update({color: new_items})

    save_json(data, filepath)
