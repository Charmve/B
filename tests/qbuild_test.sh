#!/bin/bash
set -euo pipefail

# shellcheck disable=SC1090,SC1091
. "$(dirname "${BASH_SOURCE[0]}")/test_base.sh"

ARCH="$(uname -m)"

if [[ "${ARCH}" != "x86_64" ]]; then
  warning "Please run this script on an x86_64 system."
  exit 1
fi

function expect_failure_case() {
  echo "run expect failure case ... "
}

function expect_success_case() {
  echo "run expect success case ... "
  # -it | --install)
  # Usage: qbuild --build <target_platform> <module_name_whale_dir>

  expect_success qbuild --build x9hp onboard/lite/launch_autonomy_main
  expect_success qbuild --build x9hp qbuild/examples/hiqcraft/hiqcraft
  expect_success qbuild --build j5 onboard/lite/launch_autonomy_main

  # -it | --install)
  # Usage: qbuild --install <target_platform> <module_name_whale_dir>

  expect_success qbuild --install x9hp onboard/lite/launch_autonomy_main
  expect_success qbuild --install x9hp qbuild/examples/hiqcraft/hiqcraft
  expect_success qbuild --install j5 onboard/lite/launch_autonomy_main

  # -d | --deploy)
  # Usage: qbuild --deploy <target_platform> <module_name_whale_dir> <target_platform_deploy_dir>

  expect_success qbuild --deploy x9hp onboard/lite/launch_autonomy_main
  expect_success qbuild --deploy j5_1 onboard/lite/launch_autonomy_main
  expect_success qbuild --deploy j5_2 onboard/lite/launch_autonomy_main

  # -r | --run)
  # Usage: qbuild --run <target_platform> <target_platform_binary_abstract_dir>

  expect_success qbuild --run x9hp /qcraft/qbuild/examples/hiqcraft/hiqcraft
  expect_success qbuild --run j5_1 /qcraft/onboard/lite/launch_autonomy_main
  expect_success qbuild --run j5_2 /qcraft/onboard/lite/launch_autonomy_main
  expect_success qbuild --run x9hp /qcraft/onboard/lite/launch_autonomy_main

  # -p | --pull)
  # Usage: qbuild --pull <target_platform> <remote_file_path (absolute path)> <local_path>

  expect_success qbuild --pull x9hp /qcraft/qbuild/examples/hiqcraft/hiqcraft .
  expect_success qbuild --pull j5_1 /qcraft/onboard/lite/launch_autonomy_main /qcraft
  expect_success qbuild --pull j5_2 /qcraft/onboard/lite/launch_autonomy_main ~/

  # -ut | --unittest)
  # Usage: qbuild --unittest <target_platform> <test_name>

  expect_success qbuild --unittest j5 cyber/lite/lite_writer_reader_test

  # -bm | --benchmark)
  # Usage: qbuild --benchmark <target_platform> <benchmark_name>

  expect_success qbuild --benchmark x9hp onboard/logging/logging_bm
  expect_success qbuild --benchmark j5 onboard/logging/logging_bm

  # -pf | --perf)
  # Usage: qbuild --perf <target_platform> <module_name_whale_dir>

  expect_success qbuild --perf j5 /qcraft/onboard/lite

  #-co | --coverage)
  # Usage: qbuild --coverage <target_platform> <test_dir>

  expect_success qbuild -co j5 onboard/lite/service/
  expect_success qbuild -co x9hp onboard/lite/service/

  # -so | --sonarqube)
  # Usage: qbuild --sonarqube <scan_dir>

  expect_success qbuild -sc /qcraft/onboard/lite

  # -is | --issues)
  # Usage: qbuild --issuesqbuild --issues
  expect_success qbuild --issues
}

function main() {
  cd /qcraft
  expect_success qbuild --benchmark j5 onboard/logging/logging_bm
}

main "$@"
