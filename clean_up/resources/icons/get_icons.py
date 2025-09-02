import requests
import json
import os
import sys
import argparse 
import time
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.utils import update_metadata

"""
This script:
* writes the metadata of the icons to `metadata.json` (for pushing to GitHub),
* [dev] saves the raw icon info to `[dev]icon_raw/<TERM>` 
* [dev] saves the icons to `icons/<TERM>/<COLOR>` for visual inspection

Constants in code: 
* `NUM`: number of icons to download per color
* `COLORS`: the list of colors to query icons for. 
            Skip the colors where the provider has less than `THRESHOLD` icons for the given term. 
* `THRESHOLD`: the number of icons that the provider must have for each "term-color" combination to be considered valid. 

Searching criteria: 
0. The goal is for icons in each `term-color` combination to be as homogeneous as possible.
1. For each `term-color` combination, the provider must provide at least `THRESHOLD` icons; otherwise we skip that color.
    The reason behind is if the search base is too small, the icons might end up highly heterogeneous,
    while when there is a large enough search base, and the icons are sort by default by relevance, 
    we can expect the icons to be more relevant to the search term.
2. The icons must match the search term exactly, 
    i.e., the lowercased `name` field in the response must match the lowercased `term` exactly.
3. We go through the first 5 pages of icons from the provider, 
    and only take the icons of which the name matches exactly the search term, 
    until we have `NUM` icons for each `term-color` combination.

----- SCRIPT USAGE -----
Run this in "resource/icon" directory to save icons to the right path:
```
API_KEY=<Freepik_API_key> python get_icons.py <TERM>
```
`<TERM>` is the search term, also will be used as the directory to save the requested icons.

----- DOCS -----
Getting icons from Freepik API, 
rate limits apply, see: https://www.freepik.com/developers/dashboard/limits
API reference: https://docs.freepik.com/api-reference/icons/get-all-icons-by-order

----- REDISTRIBUTION -----
Freepik icons come from Flation,
https://support.flaticon.com/s/article/Accessing-the-API-FI?language=en_US
We are not allowed to redistribute the downloaded icons. See section 7 and 8.
https://www.flaticon.com/legal

The workaround is to download metadata (ID, url of the icons) and store them as instance.json, 
only really download the icons on the fly, when GM populate the instance.
"""

# 0. configs: get search term, API key
parser = argparse.ArgumentParser(description="Download icons from Freepik API by search term.")
parser.add_argument("term", help="Search term for icons (e.g., hat, cat, phone)")
args = parser.parse_args()

term = args.term.lower()

API_KEY = os.getenv("API_KEY")

if API_KEY is None:
    raise EnvironmentError("Freepik API_KEY not set")

# 1. prep request constants
URL = "https://api.freepik.com/v1/icons"

HEADER = {"x-freepik-api-key": API_KEY }

BASE_PARAMS = {
            "term": term,
            "per_page": 100,
            "filters[shape]": "fill", 
            "filters[icon_type][]": "standard"
        }

# --- query specific constants ---
# color options
COLORS = [
            "red", "orange", "yellow",
            "green", "blue",
            "gray",  
            "black",
            # "multicolor", 
        ]
# number of icons per sub-category
NUM = 50 
# NUM = 10 
# minimum total icons per sub-category as search basis
THRESHOLD = 3000

def has_error(response): 
    if response.status_code != 200:
        if response.status_code == 404:
            print("Error 404: Not found")
        elif response.status_code == 401:
            print("Error 401: Unauthorized")
        elif response.status_code >= 500:
            print("Server error:", response.status_code)
        else:
            print(f"Unhandled status {response.status_code}: {response.text}")
        return True

def is_qualified(obj): 
    return obj['name'].lower() == term and obj['thumbnails'][0]['url'] is not None

ever_saved = False

for color in COLORS: 
    # print(f"===== Getting icons for '{term}'-{color} =====")
    icons = []
    icons_raw = []
    page_num = 1
    while len(icons) < NUM:   # go query the next page until we have enough icons
        if page_num >= 5: break  # limit to 5 pages per color, to avoid too many requests
        time.sleep(random.uniform(0, 1))
        params = {
            **BASE_PARAMS,
            "page": page_num,
            "filters[color]": color, 
        }
        response = requests.request("GET", URL, headers=HEADER, params=params)
        if has_error(response): 
            break

        data = json.loads(response.text)
        total_icons = int(data['meta']['pagination']['total'])
        if total_icons < THRESHOLD: 
            # print(f"The provider has only {total_icons} icons for {term}-{color}, skipping...")
            break

        for obj in data['data']: 
            if not is_qualified(obj): 
                continue

            icon = {
                    'freepik_id': obj['id'], 
                    'name': obj['name'].lower(),
                    'url': obj['thumbnails'][0]['url']
                }
            
            icons.append(icon)
            icons_raw.append(obj)
            
            if len(icons) >= NUM:
                break
            
        page_num += 1

    if len(icons) < NUM: 
        # print(f"Not enough icons found for {term}-{color}, found {len(icons)}, skip this color. ")
        continue

    print(f"Found {len(icons)} icons for {term}-{color}. Saving to disk..")
    ever_saved = True

    # Store icon metadata for instance generator
    update_metadata("metadata.json", term, color, icons)

    # ----- dev purpose -----
    # save the raw response
    icons_raw_dir = os.path.join("[dev]icon_raw", term)
    os.makedirs(icons_raw_dir, exist_ok=True) 
    filename = f"{term}-{color}.json"
    filepath = os.path.join(icons_raw_dir, filename)        
    
    with open(filepath, "w") as f:
        json.dump(icons_raw, f, indent=4)        
    # -----------------------        

    # ----- dev purpose -----
    # save the icon file 
    # folder = os.path.join(term, color)
    # os.makedirs(folder, exist_ok=True) 

    # for icon in icons: 

    #     icon_response = requests.get(icon['url'])
    #     filename = f"{term}-{icon['freepik_id']}.png"
    #     filepath = os.path.join(folder, filename)

    #     with open(filepath, "wb") as f:
    #         f.write(icon_response.content)
    # -----------------------        

if not ever_saved:
    print(f"No icons saved for {term} in any color, exiting.")    