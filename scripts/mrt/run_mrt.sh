#! /bin/bash
echo 'check git status ...'
git status
echo 'check git status done.'

TOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
source "${TOP_DIR}/scripts/shflags"

DEFINE_string 'mode' "stable_test" 'Mapping regression test mode.'

FLAGS "$@" || exit 1
eval set -- "${FLAGS_ARGV}"

set -e

echo "[MRT begin]  mode: ${FLAGS_mode}"
mrt_dir=${TOP_DIR}/offboard/mapping/mapping_pipeline/regression_test
mrt_mode=${FLAGS_mode} bash "${mrt_dir}"/mapping_regression_test.sh
