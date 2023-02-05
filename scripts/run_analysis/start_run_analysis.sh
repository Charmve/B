#!/bin/bash
set -e

flags=()

echo "dev mode"
bazel run offboard/dashboard/services/analysis/start_run_analysis_main -- \
  --run_analysis_server_address=8.142.91.149:3801 \
  --thread_pool_size=1 \
  --use_metric_evaluator=false \
  "${flags[@]}" \
  $@
