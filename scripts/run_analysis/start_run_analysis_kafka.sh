#!/bin/bash
set -e

flags=()

echo "remote kafka mode"

bazel run offboard/dashboard/services/analysis/run_analysis_kafka_client_test -- \
  --kafka_brokers=172.20.2.166:9092,172.20.2.167:9092,172.20.2.168:9092 \
  --thread_pool_size=4 \
  "${flags[@]}" \
  $@
