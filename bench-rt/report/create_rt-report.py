#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys

TMP_SOURCE = (
    sys.argv[1] if len(sys.argv) > 1 else "/tmp/run_output_tmpfile.txt"
)


def _find_maxlen_strings(string_dics_list):
    max_len = 0
    for string_dics in string_dics_list:
        max_len = len(string_dics["bm_name"])

    for string_dics in string_dics_list:
        if len(string_dics["bm_name"]) > max_len:
            max_len = len(string_dics["bm_name"])
    return max_len


def create_summary(data):
    unit = {
        "wall_time": " ns",
        "cpu_time": " ns",
        "time_old": " ns",
        "time_new": " ns",
        "cpu_old": " ns",
        "cpu_new": " ns",
        "iterations": "",
        "memory": " MB",
    }

    bm_max_len = _find_maxlen_strings(data)

    summary_builder = []
    summary_builder.append("\n✨ RESULTS:")
    summary_builder.append(
        "%s"
        % (
            "---------------------------------------------------------------------------------------------------".center(
                bm_max_len + 10 * 2 + 13 * 4
            )
        )
    )
    summary_builder.append(
        "%s %s %s %s %s %s %s"
        % (
            "Benchmark".ljust(bm_max_len),
            "*Time".rjust(10),
            "*CPU".rjust(10),
            "Time Old".rjust(13),
            "Time New".rjust(13),
            "CPU Old".rjust(13),
            "CPU New".rjust(13),
        )
    )
    summary_builder.append(
        "%s"
        % (
            "---------------------------------------------------------------------------------------------------".center(
                bm_max_len + 10 * 2 + 13 * 4
            )
        )
    )

    # print(lbm_result_sum)

    for lb_result in data:
        summary_builder.append(
            "%s %s %s %s %s %s %s"
            % (
                lb_result["bm_name"].ljust(bm_max_len),
                ("% .4f" % (lb_result["wall_time_diff"])).rjust(10),
                ("% .4f" % (lb_result["cpu_time_diff"])).rjust(10),
                ("% .1f%s" % (lb_result["time_old"], unit["time_old"])).rjust(13),
                ("% .1f%s" % (lb_result["time_new"], unit["time_new"])).rjust(13),
                ("% .1f%s" % (lb_result["cpu_old"], unit["cpu_old"])).rjust(13),
                ("% .1f%s" % (lb_result["cpu_new"], unit["cpu_new"])).rjust(13)
                #  (str(lb_result['wall_time']) + str(unit['wall_time'])).rjust(13),
                #  (str(lb_result['cpu_time']) + str(unit['cpu_time'])).rjust(15),
            )
        )

    summary_builder.append(
        "%s"
        % (
            "\n*Addition: in Time and CPU column, a positive number means better than the base version, and a negative number means worse than it.\nAs you can note, the values in Time and CPU columns are calculated as (new - old) / |old|".ljust(
                bm_max_len + 10 * 2 + 13 * 4
            )
        )
    )

    return "\n".join(summary_builder)


def _analysis_results_sum(collected):
    # 统计bm_name,将不同的 measurements 放入一个列表中
    lbm = []
    for benchmarking_result in collected:
        if benchmarking_result["bm_name"] not in lbm:
            lbm.append(benchmarking_result["bm_name"])

    # 结果列表
    lbm_result_sum = []
    count = 0
    # 根据lbm,生成结果列表
    for i in lbm:
        lbm_result_sum.append(
            {"bm_name": i, "wall_time": 0, "cpu_time": 0, "iterations": 0}
        )
    # 相同bm_name的 measurements 数相加

    for benchmarking_result in collected:
        for result in lbm_result_sum:
            print(result)
            if benchmarking_result["bm_name"] == result["bm_name"]:
                count += 1

                result["wall_time"] = (
                    result["wall_time"] + benchmarking_result["wall_time"]
                )
                result["cpu_time"] = (
                    result["cpu_time"] + benchmarking_result["cpu_time"]
                )
                result["iterations"] = (
                    result["iterations"] + benchmarking_result["iterations"]
                )

    for lb_result in lbm_result_sum:
        for metric, value in lb_result.items():
            if metric == "bm_name":
                continue

            # lb_result[metric] = round(value / count, 2)
            lb_result[metric] = round(value, 1)

    return lbm_result_sum


def calculate_change(old_val, new_val):
    """
    Return a float representing the decimal change between old_val and new_val.
    """
    if old_val == 0 and new_val == 0:
        return 0.0
    if old_val == 0:
        return float(new_val - old_val) / (float(old_val + new_val) / 2)
    return float(new_val - old_val) / abs(old_val)


def _analysis_results_diff(collected):
    # 统计bm_name,将不同的 measurements 放入一个列表中
    lbm = []
    for benchmarking_result in collected:
        if benchmarking_result["bm_name"] not in lbm:
            lbm.append(benchmarking_result["bm_name"])

    # 结果列表
    lbm_result_diff = []
    count = 0

    # 根据lbm,生成结果列表
    for i in lbm:
        lbm_result_diff.append(
            {
                "bm_name": i,
                "wall_time": 0,
                "cpu_time": 0,
                "wall_time_diff": 0.00,
                "cpu_time_diff": 0,
                "time_old": 0,
                "time_new": 0,
                "cpu_old": 0,
                "cpu_new": 0,
            }
        )

    # 相同bm_name的 measurements 数相减
    for benchmarking_result in collected:
        for lbm_result in lbm_result_diff:
            # if benchmarking_result['bm_name'] == lbm_result['bm_name'] and lbm_result['wall_time'] != 0:
            if benchmarking_result["bm_name"] == lbm_result["bm_name"]:
                # print("wall_time:", lbm_result['wall_time'])
                count += 1

                # print("===time ", "new", benchmarking_result['wall_time'], "old", lbm_result['wall_time'])
                # print("===cpu ", "new", benchmarking_result['cpu_time'], "old", lbm_result['cpu_time'])

                if lbm_result["wall_time"] != 0 and lbm_result["cpu_time"] != 0:
                    # print("\nwall_time ===", "new", benchmarking_result['wall_time'], "old", lbm_result['wall_time'])
                    lbm_result["time_old"] = lbm_result["wall_time"]
                    lbm_result["time_new"] = benchmarking_result["wall_time"]
                    # print("cpu_time ===", "new", benchmarking_result['cpu_time'], "old", lbm_result['cpu_time'])
                    lbm_result["cpu_old"] = lbm_result["cpu_time"]
                    lbm_result["cpu_new"] = benchmarking_result["cpu_time"]

                # print("******** ", "new", benchmarking_result['wall_time'], "old", lbm_result['wall_time'])
                lbm_result["wall_time_diff"] = calculate_change(
                    benchmarking_result["wall_time"], lbm_result["wall_time"]
                )
                lbm_result["cpu_time_diff"] = calculate_change(
                    benchmarking_result["cpu_time"], lbm_result["cpu_time"]
                )
                lbm_result["wall_time"] = (
                    benchmarking_result["wall_time"] - lbm_result["wall_time"]
                )
                lbm_result["cpu_time"] = (
                    benchmarking_result["cpu_time"] - lbm_result["cpu_time"]
                )

    return lbm_result_diff


def _analysis_performance(perf_file):

    # 定义默认结果
    wall_time = 0
    cpu_time = 0
    memory_sum = 0
    iter_count = 0

    with open(perf_file, "r") as p_file:
        txt_content = p_file.readlines()
    bm_content = [s for s in txt_content if "BM" in s]

    # if len(bm_content):
    #     return

    collected = []
    for bm_line in bm_content:  # "BM_StdAtan2  1389885 ns  1389662 ns   497"
        measurements = dict()  # {}
        for kind in ["bm_name", "wall_time", "cpu_time", "iterations"]:
            measurements[kind] = None

        bm_line_list = bm_line.rstrip().split()

        # get bm line wall_time, cpu_time, iterations
        if bm_line_list[0] == measurements["bm_name"]:
            # print(bm_line_list[0], "==", measurements["bm_name"])
            measurements["wall_time"].append(bm_line_list[1])
            measurements["cpu_time"].append(bm_line_list[3])
            measurements["iterations"].append(bm_line_list[5])
        else:
            (
                measurements["bm_name"],
                measurements["wall_time"],
                measurements["cpu_time"],
                measurements["iterations"],
            ) = (
                bm_line_list[0],
                float(bm_line_list[1]),
                float(bm_line_list[3]),
                float(bm_line_list[5]),
            )

        collected.append(measurements)

        # bm_memory_str = bm_line_list[6].rstrip("MB")
        # bm_memory = float(bm_memory_str)

        # 单项列表汇总
        # wall_time_list[bm_name] = wall_time
        # cpu_time_list[bm_name] = cpu_time
        # iter_count_list[bm_name] = iter_count

        # memory_detail[bm_name] = bm_memory

    # print(collected)

    bm_result = _analysis_results_diff(collected)
    # print(bm_result)

    return create_summary(bm_result)


def main(args):
    global file_path

    # Set up options.
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path", type=str, help="benchmark result path")
    args = parser.parse_args(args)

    file_path = args.file_path
    # print("file_path:", file_path)

    if os.path.isdir(file_path):
        # print ("it's a normal path!")
        for file in os.listdir(file_path):
            # print("file_list:", file_path+file)
            summary_text = _analysis_performance(file_path + file)
            print(summary_text, "\n")
    elif os.path.isfile(file_path):
        # print ("it's a normal file!")
        summary_text = _analysis_performance(file_path)
        print(summary_text, "\n")
    else:
        print("error - it's neither a path nor file!")


if __name__ == "__main__":
    main(sys.argv[1:])
