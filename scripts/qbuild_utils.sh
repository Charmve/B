#!/bin/bash

#########################################################
# Function :QBuild tool's utils                         #
# Platform :All Linux Based Platform                    #
# Version  :1.0.0                                       #
# Date     :2023-01-13                                  #
# Author   :Wei ZHANG                                   #
#########################################################

set -euo pipefail

QCRAFT_TOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
QBUILD_TOP_DIR="$QCRAFT_TOP_DIR/qbuild"

# shellcheck disable=SC1090,SC1091
source "${QCRAFT_TOP_DIR}/scripts/qcraft_base.sh"
# shellcheck disable=SC1090,SC1091
source "${QBUILD_TOP_DIR}/scripts/qbuild_base.sh"
source "${QCRAFT_TOP_DIR}/tools/eg/check_gtest_deps.sh"

function install_google_cli() {
  curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-416.0.0-linux-x86_64.tar.gz

  tar -xf google-cloud-cli-416.0.0-linux-x86_64.tar.gz
  ./google-cloud-sdk/install.sh
  ./google-cloud-sdk/bin/gcloud init

  rm -rf google-cloud-cli-416.0.0-linux-x86_64.tar.gz
}

function _is_target_testonly() {
  local target="$1"
  local testonly
  testonly="$(buildozer 'print testonly' "${target}")"
  [[ "${testonly}" == True || "${testonly}" == 1 ]]
}

function _is_gtest_dependent_target() {
  local deps
  deps="$(buildozer 'print deps' "$1" 2> /dev/null)"
  # NOTE(Jiaming):
  # Here we can check ONLY direct dependency on googletest.
  # Since if target_b depends on target_a which in turn depends on gtest
  # Bazel will emit the following error:
  # >> non-test target 'target_b' depends on testonly target 'target_a'
  # >> and doesn't have testonly attribute set
  [[ "${deps}" == *"@com_google_googletest//:"* ]]
}

function _testonly_check_for_gtest_dependent_target() {
  local target="$1"
  if ! _is_gtest_dependent_target "${target}"; then
    return
  fi

  if ! _is_target_testonly "${target}"; then
    error "testonly=True unspecified for gtest-dependent target ${target}"
    return 1
  fi
}

function gtest_dependency_check_for_dir() {
  local dir="$1"
  local recursive="${2:-false}"

  # shellcheck disable=SC2034
  local readonly NON_TEST_CC_PATTERNS=(
    "%cc_library"
    "%cc_binary"
    "%cuda_library"
    "%cuda_binary"
    "%qt_cc_library"
  )

  local prefix
  if [[ "${recursive}" == true ]]; then
    prefix="//${dir}/..."
  else
    prefix="//${dir}"
  fi

  # Since bazel query is relative slow (esp. on CI), instead of querying all
  # targets that deps on gtest with something like:
  # bazel query "rdeps(//onboard/...:all, @com_google_googletest//:gtest)" 2> /dev/null
  # bazel query "rdeps(//onboard/...:all, @com_google_googletest//:gtest_prod)" 2> /dev/null
  # we can query deps of all {cc,cuda}_{library,binary} and qt_cc_library targets to see if
  # one of them starts with @com_google_googletest
  for rule_patt in "${NON_TEST_CC_PATTERNS[@]}"; do
    while read -r target; do
      _testonly_check_for_gtest_dependent_target "${target}"
    done < <(buildozer 'print label' "${prefix}:${rule_patt}")
  done

  ok "Done checking gtest dependency for ${prefix}"
}

####################################################
# Find some file's dependencies
# Arguments:
#   file name (str)
# Returns:
#   Bazel target list
####################################################
function find_file_bazel_dependency() {
  local file_name=$1
  local bazel_target_name=""

  if [[ $file_name == *BUILD* ]]; then
    return
  fi

  # base_file_name=$(basename "$file_name")
  dir_name=$(dirname "$file_name")
  file_name=$(basename "$file_name" | awk -F '.' '{print $1}')

  package_contains_file=$(bazel query //"$dir_name"":""$file_name" --output=package)
  bazel_target_name=$(grep -C 5 "$file_name" "$package_contains_file"/BUILD | grep 'name' | awk -F '= "' '{print $2}' | awk -F '",' '{print $1}' | uniq -u)

  local target_names=()
  # shellcheck disable=SC2068
  for item_target in ${bazel_target_name[@]}; do
    target_names+=("//$package_contains_file:$item_target")
    # echo ${target_names[*]}
    # target_names+=("$(buildozer 'print label' $package_contains_file:$item_target")
    # info "bazel_target_name: ${item_target}"
    # if [[ "$bazel_target_name" == "$item_target" ]]; then
    #     ok "be the same."
    # else
    #     warning "${BOLD}Not same${NO_COLOR}. bazel_target_name1: $bazel_target_name, bazel_target_name: $item_target"
    # fi
  done

  echo "${target_names[@]}"
}

function find_build_target_bazel_dependency() {
  if [[ $# == 0 ]]; then
    error "Need a bazel target name, like '//onboard/lite:lite_timer'."
    exit 1
  fi
  local bazel_target_name="$1"
  local result=()
  if [[ $bazel_target_name == *offboard* ]]; then
    result+=("$(bazel query "somepath(//offboard/..., $bazel_target_name)")")
  fi
  if [[ $bazel_target_name == *onboard* ]]; then
    result+=("$(bazel query "somepath(//onboard/..., $bazel_target_name)")")
    # bazel query "allpaths(//onboard/..., $bazel_target_name)" --notool_deps # --output graph
  fi

  echo "${result[@]}"
}

function isInArray() {
  if [[ $# -lt 2 ]]; then
    echo '0'
    exit 1
  fi

  array=$1
  val=$2

  for i in "${array[@]}"; do
    [ "$i" == "$val" ] && echo '1' && exit 0
  done

  echo '0'
}

function find_depend_target_by_file() {
  local full_file_name=$1
  local dependent_build_targets=()

  bazel_target_name=$(find_file_bazel_dependency "$full_file_name")

  # shellcheck disable=SC2048
  for _target_name in ${bazel_target_name[*]}; do
    # echo "_target_name: $_target_name"
    bazel_dependency=$(find_build_target_bazel_dependency "$_target_name")
    # shellcheck disable=SC2048
    for depend_target in ${bazel_dependency[*]}; do
      # echo "   depend_target: $depend_target"

      if [[ ${#dependent_build_targets[@]} -lt 1 ]]; then
        # echo "is null"
        dependent_build_targets+=("${depend_target}")
      else
        # echo "is not null"

        # for i in ${dependent_build_targets[@]}
        # do
        #   echo "aaaaaaa: $i"
        # done

        if [[ "$(isInArray "${dependent_build_targets[*]}" "$depend_target")" == '0' ]]; then
          # echo "$depend_target not exists"
          dependent_build_targets+=("${depend_target}")
        # else
        #   # echo "$depend_target exists"
        fi
      fi
    done
  done
  echo "${dependent_build_targets[*]}"
}

function run_increase_file2target() {
  readarray -t changed_files < <(git diff --ignore-submodules --diff-filter=d --name-only)

  for one_change in "${changed_files[@]}"; do
    if [[ "${one_change}" == *".proto" ]]; then
      warning "this feature is comming ..."
    fi

    # file_base_name=$(basename $_file_name)
    # echo "file_base_name: $file_base_name"
    # echo "=====> _file_name: $one_change"

    if [[ $one_change == *.cc || $one_change == *.h ]]; then
      [[ $one_change == *.cc ]] && bazel_target_name=${one_change%.cc*}${one_change##*.cc} # || warning "qbuild: only support C"
      [[ $one_change == *.h ]] && bazel_target_name=${one_change%.h*}${one_change##*.h}    # || warning "qbuild: only support C"
      info "bazel build module_name: $bazel_target_name"
      if [[ $bazel_target_name == *_test ]]; then
        info "qbuild: run $bazel_target_name on j5."
        qbuild --run j5 "$bazel_target_name"
      else
        find_depend_target_by_file "${bazel_target_name}"
      fi
    fi
  done
}

# function main() {

#   INODE_NUM=`ls -ali / | sed '2!d' | awk {'print $1'}`
#   if [ $INODE_NUM == '2' ]; then
#       error "qbuild: need run in qcraft_cross_compile_j5 docker container."
#       exit 1
#   else
#       echo "⛵ Hello QCrafter!"
#   fi

#   cd $QCRAFT_TOP_DIR #go /qcraft

#   # parse_cmdline_args "$@"

# #   echo "On branch ${GREEN}$(git rev-parse --abbrev-ref HEAD)${NO_COLOR}"
# #   echo "Changes not staged for commit:"
# #   git diff --ignore-submodules --diff-filter=d --name-only

# #   run_increase_file2target

#   echo -e "\n${WHITE}${BOLD}All done!${NO_COLOR} ✨ 🍰 ✨"
#   echo $(date)
# }

# main "$@"
