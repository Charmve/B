import datetime  # noqa: F401
import os
import subprocess
import sys
import time

import psutil

# from absl import flags
import utils.logger as logger

# FLAGS = flags.FLAGS
# flags.DEFINE_boolean('verbose', False,
#                      'Whether to include git/Bazel stdout logs.')


def _exec_command(args, shell=False, cwd=None):
    logger.log("Executing: %s" % (args if shell else " ".join(args)))

    return subprocess.run(
        args, shell=shell, cwd=cwd, check=True, stdout=sys.stdout, stderr=sys.stderr
    )


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


def _get_pid_new():
    _pid = os.fork()  # fork反复拷贝
    if _pid == 0:
        print("A", os.getpid(), os.getppid())
    else:
        print("B", os.getpid(), os.getppid())
    return _pid


def _get_pid(run_comand):
    """Returns the pid of the server.

    Has the side effect of starting the server if none is running. Caches the
    result.
    """
    _pid = (int)(subprocess.check_output(run_comand))
    return _pid


def _get_times():
    """Retrieves and returns the used times."""
    # TODO(twerth): Getting the pid have the side effect of starting up the
    # Bazel server. There are benchmarks where we don't want this, so we
    # probably should make it configurable.
    process_data = psutil.Process(pid=_get_pid())
    cpu_times = process_data.cpu_times()
    print("====> cpu_time:", time.process_time())
    print("====> cpu_num:", process_data.cpu_num())

    return {
        "wall": time.time(),
        # 'cpu': cpu_times.user, #TODO: add domianed cpu core numbers
        # 'cpu': time.process_time(),
        "cpu": sum(cpu_times[:3]),
        "cpu_user": cpu_times.user,
        "cpu_system": cpu_times.system,
    }


print(
    subprocess_popen(
        "hyperfine --runs 5 'cd /qcraft/qbuild/examples/hiqcraft && ./hiqcraft'"
    )
)


# print(_exec_command(['cd /qcraft/qbuild/examples/hiqcraft', ' && ./hiqcraft']))
# print(_exec_command(['hyperfine', '--runs 10', './bazel-bin/qbuild/examples/hiqcraft/hiqcraft']))
