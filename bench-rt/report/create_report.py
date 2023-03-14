#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import heapq
import logging
import os
import re
import sys

import requests

_QBOT_API_ADDR = "https://qbot.qcraftai.com/api/v1"
# Please note that section must be end with ":" or "?"
_MR_DESC_PATTERN = re.compile(r"(\#{3}[\d\w\s]+)[\:\?]([^#]*)", re.S)

_RB_REPORT_SECTION = r"""### Benchmark regression test"""
_RB_REPORT_TABLE_FORMAT = "|Benchmark|*Time|*CPU|Time Old|Time New|CPU Old|CPU New|\n|:--|--:|--:|--:|--:|--:|--:|"


_QBOT_API_ADDR = "http://qbot.qcraftai.com/api/v1"

TMP_SOURCE = (
    sys.argv[1] if len(sys.argv) > 1 else "/qcraft/qbuild/tmp/run_output_tmpfile.txt"
)

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


def query_mr_info(mr_id):
    headers = {"Content-Type": "application/json"}
    url = f"{_QBOT_API_ADDR}/get/mergerequest"
    response = requests.post(url, headers=headers, json={"iid": int(mr_id)})
    if response.status_code != 200:
        logging.error(response.json())
        return None
    return response.json()


# We will only allow user to update description and title for now
def update_mr_description(mr_id, title="", description=""):
    headers = {"Content-Type": "application/json"}
    url = f"{_QBOT_API_ADDR}/update/mergerequest"
    response = requests.post(
        url,
        headers=headers,
        json={"iid": int(mr_id), "title": title, "description": description},
    )
    if response.status_code != 200:
        logging.error(response.json())
        return None
    return response.json()


def parse_mr_section_text(text):
    answers = [line.strip() for line in text.split("\n") if line.strip()]
    if not answers:
        return None
    return answers


def append_new_section_for_rb_report(text, base_commit, commit_sha):
    _EB_REPORT_VERSION = "- Base commit: {}, this mr commit: {}\n".format(
        base_commit, commit_sha
    )
    _RB_REPORT_ADDITION = (
        "> *<b>Addition</b>: <br>"
        + _EB_REPORT_VERSION
        + "- In Time and CPU column, a positive number means better than the base version, and a negative number means worse than it.\nAs you can note, the values in Time and CPU columns are calculated as (new - old) / |old|."
    )

    text += "\n\n{}:\n{}\n\n{}\n".format(
        _RB_REPORT_SECTION, _RB_REPORT_ADDITION, _RB_REPORT_TABLE_FORMAT
    )
    return text


def append_benchmark_report_addition_for_rb_report(text):
    text += "\n{}".format(_RB_REPORT_ADDITION)
    return text


def _find_maxlen_strings(string_dics_list):
    max_len = 0
    for string_dics in string_dics_list:
        max_len = len(string_dics["bm_name"])

    for string_dics in string_dics_list:
        if len(string_dics["bm_name"]) > max_len:
            max_len = len(string_dics["bm_name"])
    return max_len


def _add_lable_for_gap(input_data, max, min, topk, badk):

    if abs(input_data) > 0.06:
        if input_data < 0:
            return worst_result(input_data)
        else:
            return great_result(input_data)

    if input_data in badk:
        return bad_result(input_data)

    if input_data in topk:
        return good_result(input_data)

    if input_data == max:
        return great_result(input_data)

    if input_data == min:
        return worst_result(input_data)

    return "% .4f" % (input_data)


def bad_result(data):
    return ":small_red_triangle_down: <b>%s</b>" % format(data, ".4f")


def worst_result(data):
    return ":x: <b>%s</b>" % format(data, ".4f")


def good_result(data):
    return ":small_blue_diamond: %s" % format(data, ".4f")


def great_result(data):
    return ":fire: <b>%s</b>" % format(data, ".4f")


def append_new_rb_report(summary_text, data):
    if not data:
        logging.error(f'{"Benchmark result is none."}')
        sys.exit(1)

    wall_time_diff = []
    cpu_time_diff = []
    for item in data:
        # print("wall_time:", item["wall_time_diff"], "cpu_time:", item["cpu_time_diff"])
        wall_time_diff.append(item["wall_time_diff"])
        cpu_time_diff.append(item["cpu_time_diff"])  # no

    wall_time_max, wall_time_min = max(wall_time_diff), min(wall_time_diff)
    cpu_time_max, cpu_time_min = max(cpu_time_diff), min(cpu_time_diff)
    # print(wall_time_max, wall_time_min)

    total_bm_count = len(wall_time_diff)
    # print("length: ", total_bm_count)
    wall_time_topk = heapq.nlargest(round(total_bm_count * 0.3), wall_time_diff)
    wall_time_badk = heapq.nsmallest(round(total_bm_count * 0.3), wall_time_diff)
    # print("===> wall_time_topk:", wall_time_topk)
    # print("===> wall_time_badk:", wall_time_badk)

    cpu_time_topk = heapq.nlargest(round(total_bm_count * 0.3), cpu_time_diff)
    cpu_time_badk = heapq.nsmallest(round(total_bm_count * 0.3), cpu_time_diff)

    # summary_text += "\n"
    for lb_result in data:
        # print("===> summary_text:\n", summary_text)
        summary_text += "| %s | %s | %s | %s | %s | %s | %s |\n" % (
            lb_result["bm_name"],
            _add_lable_for_gap(
                lb_result["wall_time_diff"],
                wall_time_max,
                wall_time_min,
                wall_time_topk,
                wall_time_badk,
            ),
            _add_lable_for_gap(
                lb_result["wall_time_diff"],
                cpu_time_max,
                cpu_time_min,
                cpu_time_topk,
                cpu_time_badk,
            ),
            "% .1f%s" % (lb_result["time_old"], unit["time_old"]),
            "% .1f%s" % (lb_result["time_new"], unit["time_new"]),
            "% .1f%s" % (lb_result["cpu_old"], unit["cpu_old"]),
            "% .1f%s" % (lb_result["cpu_new"], unit["cpu_new"])
            #  (str(lb_result['wall_time']) + str(unit['wall_time'])).rjust(13),
            #  (str(lb_result['cpu_time']) + str(unit['cpu_time'])).rjust(15),
        )
        # print("===> summary_text:", summary_text)

    return summary_text


def update_description_content_for_regession_benchmark_report(
    mr_description, mr_id, commit_sha, base_commit, data
):
    matches = _MR_DESC_PATTERN.findall(mr_description)

    new_code_coverage_report_test = None
    code_coverage_report_text = None

    for m in matches:
        section = m[0]
        if _RB_REPORT_SECTION in section:
            logging.info("Find original regression benchmark report part")
            code_coverage_report_text = m[1].rstrip()
            continue

    # print("====> code_coverage_report_text:\n", code_coverage_report_text)
    if code_coverage_report_text is None:
        if not data:
            mr_description += (
                "\n\n{}:\n:100: This MR ({}) didn't affect any benchmark.".format(
                    _RB_REPORT_SECTION, commit_sha
                )
            )
            update_mr_description(mr_id, "", mr_description)
            logging.info("Congrats! Update MR description check passed.")
            sys.exit(0)

        mr_description = append_new_section_for_rb_report(
            mr_description, base_commit, commit_sha
        )
        mr_description = append_new_rb_report(mr_description, data)
        # mr_description = append_benchmark_report_addition_for_rb_report(mr_description)
    else:
        if not data:
            new_code_coverage_report_test = (
                "\n:100: This MR ({}) didn't affect any benchmark.".format(commit_sha)
            )
            mr_description = mr_description.replace(
                code_coverage_report_text, new_code_coverage_report_test
            )
            update_mr_description(mr_id, "", mr_description)
            logging.info("Congrats! Update MR description check passed.")
            sys.exit(0)

        # delete historical report
        report_table_header = ""
        for line in code_coverage_report_text.split("\n")[:8]:
            if "BM_" not in line:
                report_table_header += "\n{}".format(line)

        report_table_header += "\n"
        # print(report_table_header)

        # mr_description = append_new_section_for_rb_report(mr_description, base_commit, commit_sha)

        new_code_coverage_report_test = append_new_rb_report(report_table_header, data)
        mr_description = mr_description.replace(
            code_coverage_report_text, new_code_coverage_report_test
        )

    logging.info("After update MR description content:")
    logging.info(mr_description)

    update_mr_description(mr_id, "", mr_description)

    return True


def create_summary(data):

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
            # print(result)
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


def update_benchmark_results(mr_id, commit_sha, base_commit, data):

    if mr_id is None or not commit_sha or not base_commit:
        logging.warn(
            "Either CI_MERGE_REQUEST_IID or MR_COMMIT_SHA or BASE_COMMIT is not provided."
        )
        # parser.print_help()
        sys.exit(1)

    mr_response = query_mr_info(mr_id)
    if not mr_response:
        logging.error(f"Failed to query MR status: mr={mr_id}")
        sys.exit(1)

    mr_description = mr_response.get("description", None)
    if not mr_description:
        logging.error("MR query response doesn't have the 'description' field")
        sys.exit(1)

    # logging.info("Before update MR description content:")
    # logging.info(mr_description)

    if not update_description_content_for_regession_benchmark_report(
        mr_description, mr_id, commit_sha, base_commit, data
    ):
        logging.error("Update MR description failed")
        sys.exit(1)

    logging.info("Congrats! Update MR description check passed.")


def _analysis_performance(perf_file, mr_id, commit_sha, base_commit):

    # 定义默认结果
    wall_time = 0
    cpu_time = 0
    memory_sum = 0
    iter_count = 0

    with open(perf_file, "r") as p_file:
        txt_content = p_file.readlines()
    bm_content = [s for s in txt_content if "BM" in s]

    if not bm_content:
        logging.error(f"{perf_file} has no BM_ result.")
        update_benchmark_results(mr_id, commit_sha, base_commit, [])
        # update_mr_description(mr_id, "", ":100: Your mr({}) didn't affect any benchmark.".format(mr_id))
        sys.exit(1)

    collected = []
    for bm_line in bm_content:  # "BM_StdAtan2  1389885 ns  1389662 ns   497"
        measurements = dict()  # {}
        for kind in ["bm_name", "wall_time", "cpu_time", "iterations"]:
            measurements[kind] = None

        bm_line_list = bm_line.rstrip().split()

        # get bm line wall_time, cpu_time, iterations
        if bm_line_list[0] == measurements["bm_name"]:
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

    bm_result = _analysis_results_diff(collected)
    return bm_result


if __name__ == "__main__":
    logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

    global file_path

    # Set up options.
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--file_path",
        # type=str,
        metavar="FILE PATH",
        help="Benchmark result path",
    )
    parser.add_argument(
        "-m",
        "--mr",
        metavar="MR",
        help="Merge request ID",
    )
    parser.add_argument(
        "-c",
        "--commit_sha",
        metavar="COMMIT SHA",
        help="COMMIT SHA",
    )
    parser.add_argument(
        "-bc",
        "--base_commit",
        metavar="THIS MR COMMIT SHA",
        help="THIS MR COMMIT SHA",
    )
    parser.add_argument(
        "-n",
        "--no_affect",
        type=bool,
        metavar="AFEECT BENCHMARK",
        help="if affect benchmarking",
    )

    args = parser.parse_args()

    file_path = args.file_path
    # print("file_path:", file_path)

    mr_id = args.mr if args.mr else os.getenv("CI_MERGE_REQUEST_IID")
    commit_sha = args.commit_sha if args.commit_sha else os.getenv("CI_COMMIT_SHA")
    commit_sha = commit_sha[:7]
    base_commit = (
        args.base_commit
        if args.base_commit
        else os.getenv("CI_MERGE_REQUEST_DIFF_BASE_SHA")
    )
    base_commit = base_commit[:7] if base_commit else ""

    # print(file_path, mr_id, commit_sha, base_commit)

    if os.path.isdir(file_path):
        # print ("it's a normal path!")
        if not os.listdir(file_path):
            logging.error(f"{file_path} has no BM_ result.")
            update_benchmark_results(mr_id, commit_sha, base_commit, [])
            # update_mr_description(mr_id, "", ":100: Your mr didn't affect any benchmark.")
            sys.exit(1)
        for file in os.listdir(file_path):
            # print("file_list:", file_path+file)
            bm_result = _analysis_performance(
                file_path + file, mr_id, commit_sha, base_commit
            )
            summary_text = create_summary(bm_result)
            print(summary_text, "\n")
            update_benchmark_results(mr_id, commit_sha, base_commit, bm_result)
    elif os.path.isfile(file_path):
        # print ("it's a normal file!")
        bm_result = _analysis_performance(file_path, mr_id, commit_sha, base_commit)
        summary_text = create_summary(bm_result)
        print(summary_text, "\n")
        update_benchmark_results(mr_id, commit_sha, base_commit, bm_result)
    else:
        print("error - it's neither a path nor file!")
