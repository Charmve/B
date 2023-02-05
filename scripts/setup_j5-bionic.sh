#!/bin/bash
set -euo pipefail

TOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"

# shellcheck disable=SC1090,SC1091
source "${TOP_DIR}/scripts/docker_base.sh"


cd $TOP_DIR/qbuild
docker build -t qcraft/j5-bionic-qemu-20221230_0011:v1 -f j5-qemu.aarch64.dockerfile

function goto() {
 platform=$1
 cd ~/qcraft
 # ./scripts/start_cross_compile_docker.sh --project $platform --office suzhou
 existing_running_docker=("$(docker ps --filter name="qcraft")")
 if [ $platform == j5 ] || [ $platform == orin ]; then
    if [[ " ${existing_running_docker[*]} " =~ cross_compile_[j5,orin] ]]; then
        ./scripts/goto_cross_compile_docker.sh --project $platform
    else
        ./scripts/start_cross_compile_docker.sh --project $platform --office suzhou
        ./scripts/goto_cross_compile_docker.sh --project $platform
    fi
 elif [ $platform == x86 ]; then
    if [[ " ${existing_running_docker[*]} " =~ dev_qcraft ]]; then
        ./scripts/goto_dev_docker.sh
    else
        ./scripts/start_dev_docker.sh --office suzhou
        ./scripts/goto_dev_docker.sh
    fi
 elif [ $platform == j5_v ]; then
    docker exec -it j5 bash
 else
    echo "goto j5/j5_v/orin/x86"
    # exit 0
 fi
}

goto j5_v