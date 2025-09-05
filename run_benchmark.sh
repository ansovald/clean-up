#!/bin/bash
# Usage: scripts/run_benchmark.sh

# do this if running HuggingFace models so that the model weights are downloaded under this directory. For API-based models, it can be ignored.
export HUGGINGFACE_HUB_CACHE=/data/kosswald/huggingface_cache

# set the GPU#0 to be used for inferencing. For API-based models, it can be ignored
# export CUDA_VISIBLE_DEVICES=0
export CUDA_VISIBLE_DEVICES=3

# activate HF venv:
source /project/kosswald/paper2025/hf_venv/bin/activate
export PYTHONPATH=.:$PYTHONPATH

mkdir -p logs


games=(
"clean_up"
)

# choose models to run, from global list (clem list models) or local list (the ones in model_registry.json)

models=(
# "Meta-Llama-3.1-8B-Instruct"
# "DeepSeek-R1-0528-Qwen3-8B"
"gpt-oss-20b-nothink"
)

echo
echo "==================================================="
echo "RUNNING: Benchmark Run"
echo "==================================================="
echo


for game in "${games[@]}"; do
  for model in "${models[@]}"; do
    echo "Testing ${model} on ${game}"
    # currently, instances.json is the default file for the current run
    # to input a specific instances file, so we could also use the version number here like this: -i instances_file (no need to .json extension)
    { time clem run -g "${game}" -m "${model}"; } 2>&1 | tee logs/runtime."${game}"."${model}".log
    { time clem transcribe -g "${game}"; } 2>&1 | tee logs/runtime.transcribe."${game}".log
    { time clem score -g "${game}"; } 2>&1 | tee logs/runtime.score."${game}".log
  done
done
echo "Evaluating results"
{ time clem eval -r "results"; }

echo "==================================================="
echo "FINISHED: Benchmark Run Version"
echo "==================================================="