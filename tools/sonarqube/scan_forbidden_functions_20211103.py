# /usr/bin/python3
# -*- encoding=utf8 -*-
"""
:author zhangwei
:changelogs
    1. 20210903 zhangwei  add function: search_target_2
    2. 20211012 zhangwei default_keywords中增加["printf", "puts", "cout", "cerr"]
    3. 20211013 zhangwei （1）修改search_target中的打印格式（2）扫描出问题时，不退出，返回问题的数量与扫描成功失败
    4. 20211014 zhangwei default_keywords中增加["fputs","putc","putchar","clog","perror"]
    5. 20211026 zhangwei 增加“check_specified_file_info”相关内容的检查
"""
import argparse
import csv
import json
import logging
import multiprocessing
import os
import re
import sys
import traceback
from functools import partial
from multiprocessing import Pool

scan_tar_files = [".cpp", ".c", ".cc", ".h", ".hpp"]
default_keywords = [
    "time",
    "gettimeofday",
    "clock_gettime",
    "high_resolution_clock",
    "system_clock",
    "steady_clock",
    "fprintf",
    "fwrite",
    "fputs",
    "ofstream",
    "printf",
    "puts",
    "putc",
    "putchar",
    "cout",
    "cerr",
    "clog",
    "perror",
]
warning_keywords = []
logging.basicConfig(
    format="[%(asctime)s][%(name)s][%(levelname)s]:%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)


def except_exit(info=None, error_code=1):
    """
    :author:            zhangwei
    :date  :            20210913
    :description:       异常退出脚本
    :param info:        (str)打印信息
    :param error_code:  (int)异常退出码
    """
    if info is not None:
        logging.error(info)
    logging.error("".join(traceback.format_stack()))
    sys.exit(error_code)


def judge_rc(true_rc, expect_rc, info, exit_flag=True, error_code=1, equal_flag=True):
    """
    :author:            zhangwei
    :date  :            20210913
    :description:       判断返回码是否等于期望，不等就打印栈和退出脚本
    :param true_rc:     实际返回码
    :param expect_rc:   期望的返回码
    :param info:        (str)步骤信息
    :param exit_flag:   (bool)当实际返回码和期望的不同时，是否退出脚本，默认退出
    :param error_code:  (int)退出脚本的错误码，默认1
    :param equal_flag:  (bool)equal_flag=True预期相等，否则报错；equal_flag=False预期不相等，否则报错
    """
    if ((equal_flag is True) and (true_rc != expect_rc)) or (
        (equal_flag is False) and (true_rc == expect_rc)
    ):
        print_info = (
            "true_rc's type:%s, true_rc:%s, expect_rc's type:%s, expect_rc:%s\n info:%s"
            % (type(true_rc), true_rc, type(expect_rc), expect_rc, info)
        )
        if exit_flag:
            logging.error(print_info)
            except_exit(None, error_code)
        else:
            logging.warning(print_info)
    return


def real_match(m_keyword, line):
    if "time" not in m_keyword:
        return True
    ind = line.find(m_keyword)
    if ind == 0:
        return True
    elif ind >= 1 and line[ind - 1] in [" ", "="]:
        return True
    else:
        return False


def search_target(afile, filter_path_list, scan_allow_dict, keyword):
    """
        clock_gettime(CLOCK_ADS,&time);
        gettimeofday(&t->tic, 0);
        time_t tt = time(0);
        time(NULL)
    or
        ::clock_gettime::
        ::gettimeofday::
    """
    for fp in filter_path_list:  # 只要filter_path_list中存在要检查的路径，就return 0
        if fp and fp in afile:
            return 0
    # add by zhangwei 过滤掉scan_allow_dict中的内容
    for file_path in scan_allow_dict.keys():
        if file_path and (file_path in afile):
            for key_tmp in scan_allow_dict[file_path]:
                if (key_tmp in "all, ALL, All") or (key_tmp in keyword):
                    return 0
    lines = []
    with open(afile, "r", encoding="utf-8") as f:
        file_content = f.read()
        pattern = r"regex({keyword}\(.*\)|::{keyword}::)"
        # pattern = "{}\(.*\)|::{}::".format(keyword, keyword)
        g_match = re.findall(pattern, file_content)
        if g_match:
            line_num = 0
            for line in file_content.split("\n"):
                line_num += 1
                if (
                    line.strip().startswith("//")
                    or line.strip().startswith("/*")
                    or line.strip().startswith("*")
                ):
                    continue
                line = line.strip()
                g_match = re.findall(pattern, line)
                for m_keyword in g_match:
                    if not real_match(m_keyword, line):
                        break
                    key_elements = (
                        "Rule=Rule0  File_path={}:{}  \033[0;31;40m{}\033[0m".format(
                            afile, line_num, m_keyword
                        )
                    )
                    print(key_elements)
                    lines.append(key_elements)
    return len(lines)


def search_target_2(rule_key, afile, filter_path_list, scan_allow_dict, keyword):
    """
    :author: zhangwei
    :date: 20210903
    :param afile: Absolute path to the file
    :param filter_path_list: List of absolute paths that do not need to be checked
    :param keyword: Keywords to check
    :return:
    """
    for fp in filter_path_list:  # 只要filter_path_list中存在要检查的路径，就return 0
        if fp and fp in afile:
            return 0
    # add by zhangwei 过滤掉scan_allow_dict中的内容
    for file_path in scan_allow_dict.keys():
        if file_path and (file_path in afile):
            for key_tmp in scan_allow_dict[file_path]:
                if (key_tmp in "all, ALL, All") or (key_tmp in keyword):
                    return 0
    lines = []
    with open(afile, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if (
                line.strip().startswith("//")
                or line.strip().startswith("/*")
                or line.strip().startswith("*")
            ):
                continue
            if re.findall(keyword, line) != []:
                key_elements = (
                    "Rule={}  File_path={}:{}  \033[0;31;40m{}\033[0m".format(
                        rule_key, afile, i + 1, line
                    )
                )
                print(key_elements)
                lines.append(key_elements)
    return len(lines)


def _retrieve_keywords(keywords):
    if not keywords:
        return []
    keyword_list = keywords.split(",")
    keyword_list = [akey.strip() for akey in keyword_list]
    return keyword_list


def check_time_function(
    paths, search_target, filter_path_list, keyword_list, res_tmp, scan_allow_dict
):
    """
    :author: zhangwei
    :param paths:
    :param search_target:
    :param filter_path_list:
    :param keyword_list:
    :param res_tmp:
    :return:
    """
    pool = Pool(multiprocessing.cpu_count())
    print(
        "[ ***check time function begin. The following functions cannot be used!***]\n"
    )
    for af in paths:
        partial_func = partial(search_target, af, filter_path_list, scan_allow_dict)
        counts = pool.map(partial_func, keyword_list)
        res_tmp += sum(counts)
    pool.close()
    pool.join()
    print("[ ***check time function finish*** ]\n")
    return res_tmp


def check_fun_key_words(
    paths,
    search_target_2,
    check_fun_key_words_path,
    filter_path_list,
    res,
    scan_allow_dict,
):
    """
    :author:  zhangwei
    :date: 20210906
    :param paths:
    :param search_target_2:
    :param check_fun_key_words_path:
    :param filter_path_list:
    :param res:
    :return:
    """
    pool = Pool(multiprocessing.cpu_count())
    if check_fun_key_words_path == {}:
        print("check_fun_key_words_path={}".format(check_fun_key_words_path))
        pass
    else:
        file = open(check_fun_key_words_path, "r")
        check_fun_key_words = eval(file.read())
        file.close()
        print("check_fun_key_words={}".format(check_fun_key_words))
        print(
            "[ ******check function begin. The following functions cannot be used!******]\n"
        )
        for af in paths:
            for key in check_fun_key_words:
                partial_func = partial(
                    search_target_2, key, af, filter_path_list, scan_allow_dict
                )
                counts = pool.map(partial_func, check_fun_key_words[key])
                res += sum(counts)
        pool.close()
        pool.join()
        print("[ ******check function finish******]\n")
    return res


def _check_log_info(load_dict, check_key, check_value, exit_flag, equal_flag=True):
    print("check_key={}, check_value={}".format(check_key, check_value))
    if check_key not in load_dict["logger"].keys():
        except_exit("find level in {} failed!!!".format(load_dict["logger"].keys()))
    else:
        judge_rc(
            true_rc=load_dict["logger"][check_key],
            expect_rc=check_value,
            info="check {} failed!!!".format(check_key),
            exit_flag=exit_flag,
            equal_flag=equal_flag,
        )


def check_mlog_json(para_dict):
    file_path = para_dict["check_specified_file_path"]
    if file_path == "":
        print("This repo does not have mlog file, so it is not checked!!!")
    else:
        print("[ ******check check_mlog_json begin******]\n")
        with open(file_path, "r", encoding="utf-8") as load_f:
            load_dict = json.load(load_f)
            if "logger" not in load_dict.keys():
                except_exit("find logger in {} failed!!!".format(file_path))
            else:
                exit_flag = (
                    True if para_dict["check_specified_file_exit"] != "false" else False
                )
                _check_log_info(
                    load_dict,
                    check_key="level",
                    check_value="debug",
                    exit_flag=exit_flag,
                    equal_flag=False,
                )
                _check_log_info(
                    load_dict,
                    check_key="enable_stderr",
                    check_value=False,
                    exit_flag=exit_flag,
                    equal_flag=True,
                )
                _check_log_info(
                    load_dict,
                    check_key="enable_background_dump",
                    check_value=True,
                    exit_flag=exit_flag,
                    equal_flag=True,
                )
        print("[ ******check check_mlog_json success******]\n")


def create_allow_dict(para_dict):
    """
    此函数为生成scan_allow_list与path的对应关系
    :author:            zhangwei
    :date  :            2021021
    :return: 对应关系的字典
    """
    scan_allow_dict = {}
    if para_dict["scan_allow_list_file"] != "":
        csv_file = open(para_dict["scan_allow_list_file"], "r", encoding="utf-8")
        csv_reader = csv.reader(csv_file)
        for item in csv_reader:
            if csv_reader.line_num == 1:
                continue
            scan_allow_dict[item[0]] = item[1:]
        csv_file.close()
    return scan_allow_dict


def check_main(para_dict):
    scan_allow_dict = create_allow_dict(para_dict)
    path = para_dict["path"]
    keywords = para_dict["keywords"]
    filter_path = para_dict["filter_path"]
    check_fun_key_words_path = para_dict["check_fun_key_words_path"]
    filter_path_list = filter_path.split(",")
    filter_path_list = [pt.strip() for pt in filter_path_list]
    keyword_list = _retrieve_keywords(keywords)
    keyword_list.extend(default_keywords)
    paths = []
    for root, dirs, files in os.walk(path):
        files = [
            os.path.join(root, name)
            for name in files
            for targ in scan_tar_files
            if name.endswith(targ)
        ]
        paths.extend(files)  # 指定路径下，带某些后缀的所有需要检查文件的绝对路径，
    # step 02> Begin to check code
    res = 0
    res = check_time_function(
        paths, search_target, filter_path_list, keyword_list, res, scan_allow_dict
    )
    print("******errors num for time functions={} ******".format(res))
    res = check_fun_key_words(
        paths,
        search_target_2,
        check_fun_key_words_path,
        filter_path_list,
        res,
        scan_allow_dict,
    )
    print("******total errors num={} ******".format(res))
    # warning 类的检查，不计入res
    if warning_keywords != []:
        warn_res = check_time_function(
            paths, search_target, filter_path_list, warning_keywords, 0, scan_allow_dict
        )
        print("******warning errors num={} ******".format(warn_res))
    # check mlog 配置文件
    check_mlog_json(para_dict)

    # step 03> Judgment threshold
    expect_res = 0
    if res > expect_res:
        print("Please correct the forbidden function !!!")
    else:
        print("There are no forbidden functions, the check result is successful !!!")
    return expect_res, res


if __name__ == "__main__":
    # step 01> Parameter analysis
    param_dict = {}
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--path", help="scan source path")
    parser.add_argument(
        "-ff", "--forbidden_functions", help="functions not allow to use"
    )
    parser.add_argument(
        "--filter_path_keywords", help="filter path keywords", default=""
    )
    parser.add_argument(
        "--check_fun_key_words_path",
        help="Write the file path of the unavailable function",
        default={},
    )
    # changed by zhangwei 20211014 continueOnError不再使用，但不删除，为了兼容部分分支，用旧的模式直接跑此脚本时不报错
    parser.add_argument(
        "--continueOnError", help="Continue with errors", default="true"
    )
    parser.add_argument(
        "--check_specified_file_info",
        help="Write info of the specified file",
        default=",",
    )
    parser.add_argument(
        "--scan_allow_list_file", help="The file of scan_allow_list", default=""
    )

    args = parser.parse_args()
    param_dict["path"] = args.path
    param_dict["keywords"] = args.forbidden_functions
    param_dict["filter_path"] = args.filter_path_keywords
    param_dict["check_fun_key_words_path"] = args.check_fun_key_words_path
    param_dict["continueOnError"] = args.continueOnError
    param_dict["scan_allow_list_file"] = args.scan_allow_list_file
    param_dict["check_specified_file_path"] = args.check_specified_file_info.split(",")[
        0
    ]
    try:
        param_dict["check_specified_file_exit"] = args.check_specified_file_info.split(
            ","
        )[1]
    except Exception:
        param_dict["check_specified_file_exit"] = "false"  # 如果没有给值，默认不符合要求时，不退出
    check_main(param_dict)
