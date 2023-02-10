import argparse
import datetime
import io  # noqa: F401
import json  # noqa: F401
import os  # noqa: F401
import statistics  # noqa: F401
import subprocess
import sys


def subprocess_popen(statement):
    p = subprocess.Popen(
        statement, shell=True, stdout=subprocess.PIPE
    )  # 执行shell语句并定义输出格式
    while (
        p.poll() is None
    ):  # 判断进程是否结束（Popen.poll()用于检查子进程（命令）是否已经执行结束，没结束返回None，结束后返回状态码）
        if (
            p.wait() != 0
        ):  # 判断是否执行成功（Popen.wait()等待子进程结束，并返回状态码；如果设置并且在timeout指定的秒数之后进程还没有结束，将会抛出一个TimeoutExpired异常。）
            print("命令执行失败，请检查设备连接状态")
            return False
        else:
            re = p.stdout.readlines()  # 获取原始执行结果
            result = []
            for i in range(len(re)):  # 由于原始结果需要转换编码，所以循环转为utf8编码并且去除\n换行
                res = re[i].decode("utf-8").strip("\r\n")
                result.append(res)
            return result


def _upload_to_storage(src_file_path, storage_bucket, destination_dir):
    """Uploads the file from src_file_path to the specified location on Storage."""
    args = [
        "gsutil",
        "cp",
        src_file_path,
        "gs://{}/{}".format(storage_bucket, destination_dir),
    ]
    subprocess.run(args)


def _get_dated_subdir_for_project(project, date):
    return "{}/{}".format(project, date.strftime("%Y/%m/%d"))


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Bazel Bench Daily Report")
    parser.add_argument("--date", type=str, help="Date in YYYY-mm-dd format.")

    parsed_args = parser.parse_args(args)

    date = (
        datetime.datetime.strptime(parsed_args.date, "%Y-%m-%d").date()
        if parsed_args.date
        else datetime.date.today()
    )

    project = "bazel-bench-data"
    storage_bucket = "172.18.18.57:8000/bazel-bench"
    dated_subdir = _get_dated_subdir_for_project(project, date)

    report_tmp_file = "{}/report_{}_{}.html".format(
        "REPORTS_DIRECTORYi", project, date.strftime("%Y%m%d")
    )
    _upload_to_storage(
        report_tmp_file, storage_bucket, dated_subdir + "/{}.html".format("my_test")
    )


if __name__ == "__main__":
    sys.exit(main())


"""
bazel_bin_path = subprocess_popen("which bazel")[0]
print(bazel_bin_path)


result=subprocess_popen("bazel --version | awk -F ' ' '{print $2}'")
print("====> ", result[0])

output = list(map(lambda x: x[0], result))
print("result: ", result[0], "\noutput:", output[0])
"""
