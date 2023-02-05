#!/bin/bash
# Usage:
# ./scripts/profiling/flamegraph.sh <binary> <binary.prof> [<binary.svg>]
set -euo pipefail

TOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
source "${TOP_DIR}/scripts/qcraft_base.sh"

PROFILER_ENABLED_BINARY=
PROFILE_OF_BINARY=
GENERATED_SVG=

function usage() {
  info "Usage:"
  info "  $0 <binary> <binary.prof> [<binary.svg>]"
}

function parse_cmdline_args() {
  if [[ $# -lt 2 || $# -gt 3 ]]; then
    usage
    exit 1
  fi

  if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    usage
    exit 0
  fi

  PROFILER_ENABLED_BINARY="$1"
  if [[ ! -x "${PROFILER_ENABLED_BINARY}" ]]; then
    warning "Binary [${PROFILER_ENABLED_BINARY}] doesn't exist or is not executable!"
    return 1
  fi

  PROFILE_OF_BINARY="$2"
  if [[ ! -f "${PROFILE_OF_BINARY}" ]]; then
    warning "Profile [${PROFILE_OF_BINARY}] doesn't exist!"
    return 1
  fi

  if [[ $# -eq 3 ]]; then
    GENERATED_SVG="$3"
  else
    GENERATED_SVG="$(basename "${PROFILER_ENABLED_BINARY}").svg"
    info "The generated flamegraph svg will be saved as ${GENERATED_SVG}"
  fi
}

function run_flamegraph() {
  /usr/bin/pprof --collapsed "${PROFILER_ENABLED_BINARY}" "${PROFILE_OF_BINARY}" \
    | "${TOP_DIR}/scripts/profiling/flamegraph.pl" > "${GENERATED_SVG}" 2> /dev/null
}

function main() {
  warning "DEPRECATED: pprof from Gperftools should be DEPRECATED in the near future."
  warning "  Please use /usr/local/bin/pprof from GitHub://google/pprof instead."
  parse_cmdline_args "$@"
  run_flamegraph
  ok "Congrats! The generated flamegraph svg is saved as ${GENERATED_SVG}."
  ok "  You can open it with your web browser (e.g. Chrome) to view interactively."
}

main "$@"
