#!/bin/bash
#ref: https://github.com/bazelbuild/bazel-bench

set -euo pipefail

QCRAFT_TOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
QBUILD_TOP_DIR="$QCRAFT_TOP_DIR/qbuild"
# shellcheck disable=SC1090
source "${QCRAFT_TOP_DIR}/scripts/qcraft_base.sh"
source "${QBUILD_TOP_DIR}/scripts/qbuild_base.sh"
source "${QBUILD_TOP_DIR}/scripts/qbuild_utils.sh"

function get_all_build_targets() {
  filter=$1
  build_files="/qcraft/qbuild/tmp/tmp_result.txt"
  if [[ $filter == *bm* ]]; then
    filter_pat="_bm"
  elif [[ $filter == *test* ]]; then
    filter_pat="_test"
  else
    error "filter pattern '$filter' is invoild."
    exit 1
  fi
  
  cd /qcraft || exit
  info "filter_pat: $filter_pat"
  bazel query //onboard/... | grep "$filter_pat$" > $build_files
  cd -
}

get_all_build_targets bm

_bazel_command=$1 

for build_file in `cat $build_files`
do
     info "Processing: $build_file"
     bazel run :benchmark -- --bazel_commits=fffc26b5cc1bbe6c977af9971ed21e2e3d275d28,25be21130ba774e9f02cc39a010aafe64a3ab245 --project_source=/qcraft/ --project_commits=6dd9685b9e --data_directory=/tmp/bazel-bench-data --verbose --platform=x86 --project_label=dev-test  --collect_profile=True -- $_bazel_command  --verbose_failures $build_file
done

bazel_bench_uid=""
bazel analyze-profile /tmp/bazel-bench-data/$bazel_bench_uid

exit 0

OLD_COMMIT="ee0ec38a933e681c9f0f62567a77c424bca75080"
NEW_COMMIT="f7a74ff667d871f6a165909bf056a597592f1086"
REPO_URL="https://gitlab-cn.qcraftai.com/root/qcraft.git"
BUILD_MODULE="//onboard/lite:lite_timer"
DATA_DIR="/tmp/bazel-bench-data"

bazel run :benchmark \
-- \
--bazel_commits=$OLD_COMMIT,$NEW_COMMIT \
--project_source=/qcraft/onboard/lite/lite_timer.cc \
--data_directory=/tmp/bazel-bench-data \
--verbose \
-- build -c opt //onboard/lite:lite_timer


bazel run :benchmark \
-- \
--bazel_commits=fffc26b5cc1bbe6c977af9971ed21e2e3d275d28,25be21130ba774e9f02cc39a010aafe64a3ab245 \
--project_source=https://github.com/bsail/bazel-test-example.git \
--data_directory=/tmp/bazel-bench-data \
--verbose -- build --config=m2560 //:all

bazel run :benchmark \
-- \
--bazel_commits=fffc26b5cc1bbe6c977af9971ed21e2e3d275d28,25be21130ba774e9f02cc39a010aafe64a3ab245 \
--project_source=https://github.com/bsail/bazel-test-example.git \
--data_directory=/tmp/bazel-bench-data \
--verbose --collect_profile=True -- build \
--profile=bazel-profile --config=m2560 //:all


bazel run :benchmark -- --bazel_commits=fffc26b5cc1bbe6c977af9971ed21e2e3d275d28,25be21130ba774e9f02cc39a010aafe64a3ab245 --project_source=/home/qcraft/qcraft/ --data_directory=/tmp/bazel-bench-data --verbose --collect_profile=true -- build --profile=bazel-profile  //qbuild/examples/hiqcraft:hiqcraft

#bazel run :benchmark \
#  -- \
#  --bazel_commits=$OLD_COMMIT,$NEW_COMMIT \
#  --project_source=$REPO_URL \
#  --data_directory=$DATA_DIR \
#  --verbose \
#  -- build $BUILD_MODULE

