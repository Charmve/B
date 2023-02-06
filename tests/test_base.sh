#!/bin/bash

set -euo pipefail

QCRAFT_TOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
# shellcheck disable=SC1090,SC1091
source "${QCRAFT_TOP_DIR}/scripts/qcraft_base.sh"

# shellcheck disable=SC2188
<< COMMENT
# ref: https://blog.csdn.net/qq_38123721/article/details/108285966

  SAT					                  # Shell Automated Test 主目录
   ├── case                     # 存放用例模块的目录
   │   ├── case_a.sh            # 测试人员A用例文件
   │   └── case_b.sh            # 测试人员B用例文件
   ├── method                   # 存放方法封装模块的目录
   │   ├── assertion.sh				  # 断言函数封装模块文件
   │   └── other.sh					    # 其他函数封装模块文件
   ├── report					          # 存放测试报告的目录
   │   ├── report_0817231130		# 测试报告文件
   │   └── report_0819115441
   └── run_report.sh			      # 启动测试模块文件
COMMENT

function expect_success() {
  if "$@"; then
    ok "Success as expected: $*"
  else
    error "Failed unexpectedly: $*"
  fi
}

function expect_failure() {
  if ! "$@"; then
    ok "Failed as expected: $*"
  else
    error "Success unexpectedly: $*"
  fi
}

echo "GOOD"
