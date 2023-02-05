#!/bin/bash
set -euo pipefail

TOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"

# shellcheck disable=SC1090,SC1091
source "${TOP_DIR}/scripts/docker_base.sh"

_J5_LOG="j5.qinstall.log"

function run_bazel_install() {
  local output_dir="$1"
  local logfile
  logfile="$(mktemp /tmp/j5_log.XXXXXX)"
  bazel run --config=release --config=j5 //docker/release/j5:qbuild_install \
    -- --pre_clean --no_strip --xcompile "${output_dir}" \
    | tee -a "${logfile}"
  mv "${logfile}" "${output_dir}/${_J5_LOG}"
}

function compute_j5_tag() {
  awk -F'=' '$1 == "j5-sysroot" {print $2}' "${TOP_DIR}/docker/TAG"
}

function run_rpath_fix() {
  local output_dir="$1"
  cp "${TOP_DIR}/docker/release/rpath_fix.py" "${output_dir}/"

  docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
  docker_login_aliyun_registry_ro

  local j5_tag
  j5_tag="$(compute_j5_tag)"

  local j5_img
  j5_img="${ALIYUN_REGISTRY}/${AARCH64_DEV_REPO}:${j5_tag}"

  command_to_run=(
    "/qcraft/rpath_fix.py"
    "--prefix=${output_dir}"
    "/qcraft/${_J5_LOG}"
  )

  docker run --rm -v "${output_dir}:/qcraft" "${j5_img}" "${command_to_run[@]}"
  info "Congratulations! J5 package was successfully released at directory ${output_dir}"
}

function main() {
  # Ensure no GPU for J5/X9HP builds
  sed -i '/--config=cuda_nvcc/d' "${TOP_DIR}/ci.bazelrc" &> /dev/null || true

  local output_dir
  # output_dir="${1:-${TOP_DIR}/data/bj5}"
  output_dir="${TOP_DIR}/qbuild/output/bj5"

  run_bazel_install "${output_dir}"

  run_rpath_fix "${output_dir}"
}

main "$@"
