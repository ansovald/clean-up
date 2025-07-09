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
Adding a grandchild level key-value pair to the JSON file at filepath. 
{
    "normal": {
        "cake": [
            {
                "id": 1,
                "name": "Chocolate Cake",
                "url": "https://example.com/chocolate_cake.png"
            },
            // ...
        ], 
        // ...
    }, 
    "abstract:" {
        "abstract": [
            {
                "id": 2,
                "name": "Abstract Cake",
                "url": "https://example.com/abstract_cake.png"
            },
            // ...
        ]
    }
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
