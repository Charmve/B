#!/bin/bash

set -euo pipefail

QCRAFT_TOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
# shellcheck disable=SC1090,SC1091
source "${QCRAFT_TOP_DIR}/scripts/qcraft_base.sh"

# We define the fail function early so we can use it when detecting the JDK
# See https://github.com/bazelbuild/bazel/issues/2949,
function fail() {
  local exitCode=$?
  echo "================== $exitCode"
  if [[ $exitCode == *failed* ]]; then
    echo "yes"
    exitCode=1
  fi
  # echo >&2
  # echo "ERROR: $*" >&2
  echo $exitCode
}

# fail $1
