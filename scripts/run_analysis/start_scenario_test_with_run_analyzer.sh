#!/bin/bash
set -e

flags=()

echo "run scenario test with run analyzer"

scripts/run_scenario_test.sh --thread_pool_size=1 --china_mode=false --test_sets=must-pass \
  --type=PRESUBMIT --user=wei --jobs_server=sim-server-cn.qcraftai.com:3401 \
  --enable_run_analysis=true \
  --run_analysis_server_address=analysis-cn-staging.qcraftai.com:3801 \
  --run_analysis_config_file=offboard/dashboard/services/analysis/config/run_analysis_config.pb.txt \
  "${flags[@]}" \
  $@
