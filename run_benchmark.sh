#!/bin/bash

set -euo pipefail

QCRAFT_TOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
QBUILD_TOP_DIR="$QCRAFT_TOP_DIR/qbuild"

# shellcheck disable=SC1090,SC1091
source "${QCRAFT_TOP_DIR}/scripts/qcraft_base.sh"
source "${QBUILD_TOP_DIR}/scripts/qbuild_base.sh"
source "${QBUILD_TOP_DIR}/scripts/qbuild_utils.sh"

printf "On branch ${GREEN}$(git rev-parse --abbrev-ref HEAD)${NO_COLOR} ${BLUE}($(git rev-parse --short HEAD))${NO_COLOR}\n"
info "qbuild: changes not staged for commit:"
git diff --ignore-submodules --diff-filter=d --name-only # | grep -E '_bm|_test'

runs=5

# function _single_run() {

# }

function run_increase_file2target() {
  readarray -t changed_files < <(git diff --ignore-submodules --diff-filter=d --name-only)

  for one_change in "${changed_files[@]}"; do
    if [[ $one_change == *.proto || $one_change == *.sh || $one_change == *.py ]]; then
      warning "Just testing onboard code in real car, ignore .proto, .sh, .py ."
    fi

    # file_base_name=$(basename $_file_name)
    # echo "file_base_name: $file_base_name"
    echo "=====> _file_name: $one_change"

    _is_first_prerun="True"

    if [[ $one_change == *.cc || $one_change == *.h ]]; then
      [[ $one_change == *.cc ]] && bazel_target_name=${one_change%.cc*}${one_change##*.cc} # || warning "qbuild: only support C"
      [[ $one_change == *.h ]] && bazel_target_name=${one_change%.h*}${one_change##*.h}    # || warning "qbuild: only support C"
      info "bazel build module_name: $bazel_target_name"
      dir_name=$(dirname $bazel_target_name)
      base_file_name=$(basename $bazel_target_name)

      RUN_OUTPUT_FILE="$QBUILD_TOP_DIR/tmp/run_output-${dir_name/\//_}_$base_file_name-$(date "+%Y%m%d_%H%M%S").txt"

      info "base_file_name: $base_file_name, dir_name: $dir_name"
      if [[ $bazel_target_name == *_test || $bazel_target_name == *_bm ]]; then
        info "qbuild: run "//$dir_name:$base_file_name" on $1."
        if [[ $1 == 'j5' ]] || [[ $1 == *x9* ]]; then
          qbuild --run j5 $bazel_target_name
        else
          if [[ _is_first_prerun == "True" ]]; then
            info "Pre-runing "//$dir_name:$base_file_name" ..."
            bazel run "//$dir_name:$base_file_name"
            _is_first_prerun == "False"
          else
            for i in {1..5..1}; do
              info "Starting benchmark run $i/$runs:"
              bazel run "//$dir_name:$base_file_name" 2>&1 | tee -a $RUN_OUTPUT_FILE
              echo "\n\n\n" | tee -a $RUN_OUTPUT_FILE
              info "RUN_OUTPUT_FILE: $RUN_OUTPUT_FILE"
            done

            # MAKE SUMMARY
            grep "BM" $RUN_OUTPUT_FILE

          fi
        fi
      else
        find_depend_target_by_file ${bazel_target_name}
      fi
    fi
  done
}

run_increase_file2target x86

# find_depend_target_by_file onboard/lite/lite_timer.h
