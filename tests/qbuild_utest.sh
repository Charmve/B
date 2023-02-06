#!/bin/bash

#########################################################
# Function :QBuild tool's unit test                     #
# Platform :All Linux Based Platform                    #
# Version  :1.0.0                                       #
# Date     :2023-01-13                                  #
# Author   :Wei ZHANG                                   #
#########################################################

set -euo pipefail

## TODO[ZHANGWEI] https://github.com/kward/shunit2

# shellcheck disable=SC1090,SC1091
. "$(dirname "${BASH_SOURCE[0]}")/test_base.sh"
