import glob
import os
import json
import subprocess

from clemcore.clemgame.metrics import BENCH_SCORE

from resources.utils.metrics import MetricCalculator, ingredients_registry

"""
This script is called after the way to compute (sub) metrics has been changed, 
in MetricsCalculator in `resources/utils/metrics.py`. It does the following:

    - Find all `interactions.json` files in the results directory
    - Change `interaction.json`
    - call `clem transcribe` 
    - call `clem score`
"""

root_dir = os.path.dirname(__file__)  

# results/<MODEL>/<GAME>/<EXPERIMENT>/<EPISODE>/interactions.json
pattern = os.path.join(root_dir, "results", "*", "*", "*", "*", "interactions.json")

files = glob.glob(pattern)

for file in files: 
    print(f"Processing file: {file}")

    interactions = None
    with open(file, 'r') as f:
        interactions = json.load(f)
    
    # extract ingredients, compute sub-metrics and bench score
    ingredients = {}    
    for key in ingredients_registry: 
        assert key in interactions, f"Key '{key}' not found in {file}"
        ingredients[key] = interactions[key]
    
    metrics_calculator = MetricCalculator(ingredients)
    sub_metrics, bench_score = metrics_calculator.compute_metrics()

    # update interactions with sub_metrics_string and bench_score_string
    bench_score_string = f"* {BENCH_SCORE}: {float(bench_score):.2f}\n"

    sub_metrics_string = ""
    for key, val in sub_metrics.items(): 
        sub_metrics_string += f"* {key}: {float(val):.2f}\n"

    action_type = 'dev:game_finished'
    action_content = f"{bench_score_string}\n-------\n{sub_metrics_string}"

    for obj in interactions['turns'][-1]: 
        if obj['action']['type'] == action_type: 
            print(f"Replacing old content:\n{obj['action']['content']} with new content:\n{action_content}")

            obj['action']['content'] = action_content
            break

    with open(file, "w", encoding="utf-8") as f:
        json.dump(interactions, f, ensure_ascii=False, indent=2)


subprocess.run(["clem", "transcribe"])
subprocess.run(["clem", "score"])        

