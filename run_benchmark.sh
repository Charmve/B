#!/bin/bash

# set -euo pipefail

QCRAFT_TOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
QBUILD_TOP_DIR="$QCRAFT_TOP_DIR/qbuild"

# shellcheck disable=SC1090,SC1091
. "${QCRAFT_TOP_DIR}/scripts/shflags"

# shellcheck disable=SC1090,SC1091
. "${QCRAFT_TOP_DIR}/scripts/qcraft_base.sh"

# DEFINE_boolean 'local' "${FLAGS_TRUE}" 'local changes benchmark'
DEFINE_boolean 'ci' "${FLAGS_FALSE}" 'benchmarking previous changes on ci'
DEFINE_boolean 'cpuonly' "${FLAGS_FALSE}" 'bazel build on cpu only mode'
DEFINE_string 'target_platform' "" 'Build a/o run at which platform, eg: x86_cpuonly, j5, x9hp, drive_orin, etc.'

# shellcheck disable=SC1090,SC1091
source "${QBUILD_TOP_DIR}/scripts/qbuild_utils.sh"

runs=2
PLATFORM="${FLAGS_target_platform}"
platforms=(j5 x86_64_cpu x86_64_gpu x9hp drive_orin)
current_commit=$(git rev-parse --short HEAD)
BASE_COMMIT=
RUN_OUTPUT_PATH="/tmp/bench_results"
RUN_OUTPUT_FILE=
BAZEL_FLAGS=

bazel_flags=()

if [ "${FLAGS_ci}" -eq ${FLAGS_TRUE} ]; then
  if [[ $CI_MERGE_REQUEST_IID ]]; then
    MR_ID=$CI_MERGE_REQUEST_IID
  else
    MR_ID=
  fi
else
  MR_ID=
fi

function determine_build_flags() {
  if [ -n "${BAZEL_FLAGS}" ]; then
    bazel_flags+=("$BAZEL_FLAGS")
  else
    info "qbuild: ci has no additional bazel flags."
  fi

  if [[ "${PLATFORM}" == "x86_64_cpu" ]]; then
    bazel_flags+=("--config=cpu")
  elif [[ "${PLATFORM}" == "x86_64_gpu" ]]; then
    bazel_flags+=("--config=gpu")
  elif [[ "${PLATFORM}" == "j5" ]]; then
    bazel_flags+=("--config=j5")
  elif [[ "${PLATFORM}" == "x9hp" ]]; then
    bazel_flags+=("--config=x9hp")
  elif [[ "${PLATFORM}" == "drive_orin" ]]; then
    bazel_flags+=("--config=drive_orin")
  else
    bazel_flags+=("--config=gpu")
  fi

  if [ "${FLAGS_cpuonly}" -eq ${FLAGS_TRUE} ]; then
    PLATFORM="cpu"
  fi

  if [ ${#bazel_flags[@]} ]; then
    info "qbuild: Bazel flags '${bazel_flags[*]}'"
  else
    info "qbuild: No bazel flags."
  fi
}

function init() {
  if [[ ! "${platforms[*]}" =~ $PLATFORM ]]; then
    error "qbuild: $PLATFORM is not exists."
    exit 1
  fi

  determine_build_flags

  if [ "${FLAGS_ci}" -eq ${FLAGS_TRUE} ]; then
    info "Regression benchmarking on ci ..."
    printf "On branch ${GREEN}%s${NO_COLOR} ${BLUE}(%s)${NO_COLOR}\n" "$(git rev-parse --abbrev-ref HEAD)" "$(git rev-parse --short HEAD)"
    info "qbuild: changes for commit($current_commit):"
    git show --raw "$current_commit" | grep -E 'M|A' | awk -F 'M' '{print $2}' | awk '$1=$1' | uniq -u
  else
    printf "On branch ${GREEN}%s${NO_COLOR} ${BLUE}(%s)${NO_COLOR}\n" "$(git rev-parse --abbrev-ref HEAD)" "$(git rev-parse --short HEAD)"
    info "qbuild: changes not staged for commit:"
    git diff --ignore-submodules --diff-filter=d --name-only # | grep -E '_bm|_test'
  fi

  if [[ ! -d $RUN_OUTPUT_PATH ]]; then
    mkdir $RUN_OUTPUT_PATH
  fi
}

function _single_run() {
  build_target_name=$1
  # error -e "\n\n$build_target_name"
  dir_name=$(echo "$build_target_name" | awk -F ':' '{print $1}')
  dir_name=${dir_name//\/\//} #delete '//'

  base_file_name=$(echo "$build_target_name" | awk -F ':' '{print $2}')

  RUN_OUTPUT_FILE="$RUN_OUTPUT_PATH/run_output-${dir_name//\//_}_$base_file_name.txt"

  if [[ $build_target_name == *bm ]]; then
    info "${GREEN}Pre-runing ""$build_target_name"" ...${NO_COLOR}"
    bazel run -c opt "${bazel_flags[*]}" --verbose_failures --spawn_strategy=local "$build_target_name"

    # for i in {1..2..1}; do # dont modified this num
    # info "${GREEN}Starting benchmark run $i/$runs:${NO_COLOR}"
    if [[ $(grep -c 'Benchmark' "$RUN_OUTPUT_FILE") -ge 2 ]]; then
      echo "" > "$RUN_OUTPUT_FILE"
    fi

    start=$(date +%s)
    bazel run -c opt "${bazel_flags[*]}" --verbose_failures --spawn_strategy=local "$build_target_name" 2>&1 | tee -a "$RUN_OUTPUT_FILE"
    end=$(date +%s)
    echo -e "\n\n" | tee -a "$RUN_OUTPUT_FILE"
    info "RUN_OUTPUT_FILE: $RUN_OUTPUT_FILE, \n      Elapsed time: $((end - start))s"
    # done

    # MAKE SUMMARY
    # python "${QBUILD_TOP_DIR}"/qbuild-bench/report/create_report.py "$RUN_OUTPUT_FILE"
  else
    info "qbuild benchmark: Only ${BOLD}build${NO_COLOR} test, as '$build_target_name' is not a gbench target."
    # bazel build -c opt --verbose_failures "$build_target_name"
  fi
}

function _single_run_compare() {
  build_target_name=$1
  # echo -e "\n\n$build_target_name"

  dir_name=$(echo "$build_target_name" | awk -F ':' '{print $1}')
  dir_name=${dir_name//\/\//} #delete '//'

  base_file_name=$(echo "$build_target_name" | awk -F ':' '{print $2}')

  RUN_OUTPUT_FILE="$RUN_OUTPUT_PATH/run_output-${dir_name//\//_}_$base_file_name-$(date "+%Y%m%d_%H%M%S").txt"

  if [[ $build_target_name == *bm ]]; then
    info "${GREEN}Pre-runing ""$build_target_name"" ...${NO_COLOR}"
    bazel run -c opt "${bazel_flags[*]}" --verbose_failures --spawn_strategy=local "$build_target_name"

    for i in {1..2..1}; do # dont modified this num
      info "${GREEN}Starting benchmark run $i/$runs:${NO_COLOR}"
      bazel run -c opt "${bazel_flags[*]}" --verbose_failures --spawn_strategy=local "$build_target_name" 2>&1 | tee -a "$RUN_OUTPUT_FILE"
      echo -e "\n\n" | tee -a "$RUN_OUTPUT_FILE"
      info "RUN_OUTPUT_FILE: $RUN_OUTPUT_FILE"
    done

    # MAKE SUMMARY
    python "${QBUILD_TOP_DIR}"/qbuild-bench/report/create_report.py "$RUN_OUTPUT_FILE"
  else
    info "qbuild benchmark: Only ${BOLD}build${NO_COLOR} test, as '$build_target_name' is not a gbench target."
    # bazel build -c opt --verbose_failures "$build_target_name"
  fi
}

function _get_changed_files_local_diff() {
  readarray -t changed_files < <(git diff --ignore-submodules --diff-filter=d --name-only | grep -E '\.h$|\.cc$')

  echo "${changed_files[*]}"

  #   for one_change in "${changed_files[@]}"; do
  #     echo "$one_change"
  #   done
}

function _get_changed_files_by_commit() {
  commit=$(git rev-parse --short HEAD)
  ## git show --raw $commit
  readarray -t changed_files < <(git show --raw "$commit" | grep "M" | awk -F 'M' '{print $2}' | awk '$1=$1' | uniq -u)

  echo "${changed_files[*]}"

  #   for one_change in "${changed_files[@]}"; do
  #     echo "$one_change"
  #   done
}

function benchmark_regression() {

  rm -f $RUN_OUTPUT_PATH/*

  if [ "${FLAGS_ci}" -eq ${FLAGS_TRUE} ]; then
    # shellcheck disable=SC2178
    changed_files=$(_get_changed_files_by_commit)
  else
    # shellcheck disable=SC2178
    changed_files=$(_get_changed_files_local_diff)
  fi

  bazel_target_name=

  no_affect_benchmark_flag='False'
  # shellcheck disable=SC2048
  for one_change in ${changed_files[*]}; do
    # echo "one_change: $one_change"
    [[ $one_change == *.cc ]] && bazel_target_name=${one_change%.cc*}${one_change##*.cc} # || warning "qbuild: only support C"
    [[ $one_change == *.h ]] && bazel_target_name=${one_change%.h*}${one_change##*.h}    # || warning "qbuild: only support C"

    if [[ -n $bazel_target_name ]]; then
      no_affect_benchmark_flag='True'

      # info "bazel build module_name: $bazel_target_name"
      dir_name=$(dirname "$bazel_target_name")
      base_file_name=$(basename "$bazel_target_name")

      AffectedBuildTarget=$(find_depend_target_by_file "$bazel_target_name")

      info "${GREEN}Starting benchmark run on ${NO_COLOR} ${BLUE}$current_commit${NO_COLOR}"

      no_benchmark_test_flag='False'
      # shellcheck disable=SC2068
      for build_target in ${AffectedBuildTarget[@]}; do
        if [[ $build_target == *bm ]]; then
          info "Single run: $build_target ${GREEN}($current_commit)${NO_COLOR}"
          _single_run "$build_target"
          no_benchmark_test_flag='True'
        fi
      done

      if [[ $no_benchmark_test_flag == 'False' ]]; then
        info "Didn't affect any benchmark."
        # python "${QCRAFT_TOP_DIR}"/qbuild/qbuild-bench/report/create_report.py --no_affect=1
        break
      fi

      if [ "${FLAGS_ci}" -eq ${FLAGS_TRUE} ]; then
        # checkout previous version
        git reset --hard HEAD^
        sleep 2s
      else
        git stash
        # git checkout .
      fi
      current_commit_tmp=$(git rev-parse --short HEAD)
      BASE_COMMIT=$current_commit_tmp
      info "${GREEN}Starting benchmark run on ${NO_COLOR} ${BLUE}$current_commit_tmp${NO_COLOR}"

      # shellcheck disable=SC2068
      for build_target in ${AffectedBuildTarget[@]}; do
        if ! bazel query "$build_target"; then
          warning "qbuild: base version($current_commit_tmp) has no $build_target."
          continue
        fi
        info "Single run: $build_target ${GREEN}($current_commit_tmp)${NO_COLOR}"
        _single_run "$build_target"
      done

      if [ "${FLAGS_ci}" -eq ${FLAGS_TRUE} ]; then
        git reset --hard "$current_commit"
      else
        git stash pop
      fi
    fi
  done

  if [[ $no_affect_benchmark_flag == 'False' ]]; then
    info "Your mr didn't affect any benchmark."
  fi

  # MAKE SUMMARY
  info "$RUN_OUTPUT_PATH/ --mr=$MR_ID --commit_sha=$current_commit --base_commit=$BASE_COMMIT"
  python "${QBUILD_TOP_DIR}"/qbuild-bench/report/create_report.py --file_path="$RUN_OUTPUT_PATH/" --mr="$MR_ID" --commit_sha="$current_commit" --base_commit="$BASE_COMMIT"
}

function run_increase_file2target() {
  readarray -t changed_files < <(git diff --ignore-submodules --diff-filter=d --name-only | grep -E '\.h$|\.cc$')

  #   commit=$(git rev-parse --short HEAD)
  #   readarray -t changed_files < <(git show --raw "$commit" | grep "M" | awk -F 'M' '{print $2}' | awk '$1=$1' | uniq -u)

  for one_change in "${changed_files[@]}"; do
    echo "one_change: $one_change"
    if [[ $one_change == *.proto || $one_change == *.sh || $one_change == *.py ]]; then
      warning "Just testing onboard code in real car, ignore .proto, .sh, .py ."
    fi

    if [[ $one_change == *.cc || $one_change == *.h ]]; then
      [[ $one_change == *.cc ]] && bazel_target_name=${one_change%.cc*}${one_change##*.cc} # || warning "qbuild: only support C"
      [[ $one_change == *.h ]] && bazel_target_name=${one_change%.h*}${one_change##*.h}    # || warning "qbuild: only support C"
      # info "bazel build module_name: $bazel_target_name"
      dir_name=$(dirname "$bazel_target_name")
      base_file_name=$(basename "$bazel_target_name")

      RUN_OUTPUT_FILE="$RUN_OUTPUT_PATH/run_output-${dir_name//\//_}_$base_file_name-$(date "+%Y%m%d_%H%M%S").txt"

      if [[ $bazel_target_name == *_test || $bazel_target_name == *_bm ]]; then
        # info "base_file_name: $base_file_name, dir_name: $dir_name"
        # shellcheck disable=SC2140
        info "qbuild benchmark: run "//"$dir_name":"$base_file_name"" on $1."
        if [[ $1 == 'j5' ]] || [[ $1 == *x9* ]]; then
          qbuild --run j5 "$bazel_target_name"
        else # run on x86
          if [[ $base_file_name == *test ]]; then
            bazel test -c opt --verbose_failures --spawn_strategy=local "//$dir_name:$base_file_name"
          fi
          if [[ $base_file_name == *bm ]]; then
            # shellcheck disable=SC2140
            info "${GREEN}Pre-runing "//"$dir_name":"$base_file_name"" ...${NO_COLOR}"
            bazel run -c opt "${bazel_flags[*]}" --verbose_failures --spawn_strategy=local "//$dir_name:$base_file_name"

            for i in {1..2..1}; do # dont modified this num
              info "${GREEN}Starting benchmark run $i/$runs:${NO_COLOR}"
              bazel run -c opt "${bazel_flags[*]}" --verbose_failures --spawn_strategy=local "//$dir_name:$base_file_name" 2>&1 | tee -a "$RUN_OUTPUT_FILE"
              echo -e "\n\n" | tee -a "$RUN_OUTPUT_FILE"
              info "RUN_OUTPUT_FILE: $RUN_OUTPUT_FILE"
            done

            # MAKE SUMMARY
            python "${QBUILD_TOP_DIR}"/qbuild-bench/report/create_report.py "$RUN_OUTPUT_FILE"
          fi
        fi
      else
        # info "qbuild benchmark: not .cc or .h file"
        AffectedBuildTarget=$(find_depend_target_by_file "$bazel_target_name")

        # shellcheck disable=SC2068
        for build_target in ${AffectedBuildTarget[@]}; do
          info "Single run: $build_target ${GREEN}($current_commit)${NO_COLOR}"
          _single_run_compare "$build_target"
        done
      fi
    fi
  done
}

function main() {
  # get shflags from commandline(must called here)
  FLAGS "$@" || exit $?
  eval set -- "${FLAGS_ARGV}"

  init

  benchmark_regression

  # local platform=${1:-"x86"}
  # run_increase_file2target "$platform"

  # _single_run "//onboard/math:fast_math_bm"

  # find_depend_target_by_file onboard/lite/lite_timer.h
  # _get_changed_files_by_commit

  info "Run Successfully!"
}

main "$@"
