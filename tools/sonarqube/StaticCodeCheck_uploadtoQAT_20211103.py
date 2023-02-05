# !/usr/bin/python
# -*- encoding=utf8 -*-
"""
 author: zhangwei
 date 20211013
 @summary：
    upload results of static code check to QAT
 @steps:
    1. analytical_parameters
    2. executing check scripts and upload info to QAT
        *> 对于scan_forbidden_functions, 执行检查，并将结果重新赋值，上传给QAT后端
        *> 执行sonarqube，将ci传回来的结果整理，并将结果重新赋值，上传给QAT后端
        *> 对于autosar，执行analyze_parasoft_report，并将结果重新赋值，上传给QAT后端
        *> 对于metrics，执行analyze_parasoft_report，并将结果重新赋值，上传给QAT后端
 @changelog：
    1. 20211020 a)增加代码覆盖率与单元测试结果的信息，并将结果上传给后端；b)给缺少注释的函数按照注释规则补充注释；
"""
import argparse
import csv
import logging
import os
import signal
import subprocess
import sys
import time
import traceback
from threading import Timer

import requests


class UploadToQAT(object):
    def __init__(self):
        logging.basicConfig(
            format="[%(asctime)s][%(name)s][%(levelname)s]:%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            level=logging.DEBUG,
        )
        self.failed = "FAILURE"
        self.success = "SUCCESS"
        self.continueOnError = "True"
        # todo 增加了_20211103
        self.name_dict_path = "name_dict_info_20211103.csv"

    @staticmethod
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

    @staticmethod
    def run_command_shot_time(cmd, node_ip=None, print_flag=True, timeout=None):
        """
        :author:             zhangwei
        :date:               20211105
        :description:        执行shell命令(短时间运行的命令),适用于linux和windows
        :param cmd:          (str)要执行的命令
        :param node_ip:            执行cmd的节点
        :param print_flag:   (bool)是否需要打印执行的命令和命令执行的结果,默认值:打印
        :param timeout:      命令超时时间
        """
        if node_ip:
            cmd = 'ssh {} "{}"'.format(node_ip, cmd)
        if print_flag:
            logging.info("cmd: %s" % cmd)
        if timeout is None:
            process = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            output, unused_err = process.communicate()
            retcode = process.poll()
        else:
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,
            )

            def kill():
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)

            timer = Timer(timeout, kill)
            timer.start()
            output, unused_err = process.communicate()
            retcode = process.poll()
            timer.cancel()
        if output != "" and print_flag is True:
            logging.info("stdout: %s" % output)
        return retcode, output

    def create_name_dict(self):
        """
        此函数为生成repo_分支名，与第一模块名、第二模块名、项目名的对应关系
        :author:            zhangwei
        :date  :            2021021
        :return: 对应关系的字典
        """
        csv_file = open(self.name_dict_path, "r", encoding="utf-8")
        csv_reader = csv.reader(csv_file)
        name_dict = {}
        for item in csv_reader:
            if csv_reader.line_num == 1:
                continue
            project_name = ",".join(str(p) for p in item[3].split("/"))
            name_dict[item[0]] = {
                "first_module_name": item[1],
                "second_module_name": item[2],
                "project_name": project_name,
                "continueOnError": item[4],
            }
        csv_file.close()
        return name_dict

    def wget_file(self, link_list):
        for link in link_list:
            # 删除旧文件
            file_name = link.split("/")[-1]
            cmd = "rm {}".format(file_name)
            self.run_command_shot_time(cmd)
            # 下载新文件
            cmd = "wget {}".format(link)
            rc, output = self.run_command_shot_time(cmd)
            if rc != 0:
                self.except_exit("cmd={}, \nresuld=Failed".format(cmd))

    @staticmethod
    def analytical_parameters():
        """解析外部传入的参数
        :author:             zhangwei
        :date:               20211013
        :return: 参数字典
        """
        # 1 获取外部传参
        param_dict = {}
        parser = argparse.ArgumentParser()
        parser.add_argument("--repo_name", help="The name of repo")
        parser.add_argument("--branch_name", help="The name of branch")
        parser.add_argument("--platform", help="Choose from [devops, gitlab]")
        parser.add_argument(
            "--check_type",
            help="Choose from [scan_forbidden_functions, sonarqube, autosar, metrics,"
            "unittest_and_coverage]",
        )
        parser.add_argument("--commit_id", help="The id of commit")
        parser.add_argument("--pipeline_link", help="The link of pipeline")
        parser.add_argument("--report_link", help="The link of reports")
        parser.add_argument(
            "--continueOnError", help="Continue with errors", default="true"
        )

        # scan_forbidden_functions 的参数
        parser.add_argument("-p", "--path", help="scan source path", default="")
        parser.add_argument(
            "-ff",
            "--forbidden_functions",
            help="functions not allow to use",
            default="",
        )
        parser.add_argument(
            "--filter_path_keywords", help="filter path keywords", default=""
        )
        parser.add_argument(
            "--check_fun_key_words_path",
            help="Write the file path of the unavailable function",
            default={},
        )
        parser.add_argument(
            "--check_specified_file_info",
            help="Write info of the specified file",
            default="",
        )
        parser.add_argument(
            "--scan_allow_list_file", help="The file of scan_allow_list", default=""
        )
        # sonarqube的参数
        parser.add_argument(
            "--QualityGateStatus", help="QualityGateStatus of sonarqube", default=""
        )
        parser.add_argument(
            "--threshold_info", help="The threshold_info of sonarqube", default=""
        )
        # parasoft的参数
        parser.add_argument("--urls", help="Url of parasoft reports", default="")
        parser.add_argument("--p0_threshold", help="Threshold of P0 level", default=0)
        parser.add_argument("--p1_threshold", help="Threshold of P1 level", default=200)

        # unittest_and_coverage 的参数
        parser.add_argument(
            "--unittest_log_path", help="The path of unittest.log", default=""
        )
        parser.add_argument(
            "--coverage_log_path", help="The path of coverage.log", default=""
        )

        # 2 解析外部传参
        args = parser.parse_args()
        param_dict["repo_name"] = args.repo_name
        if "refs/heads/" in args.branch_name:
            param_dict["branch_name"] = args.branch_name.split("refs/heads/")[1]
        else:
            param_dict["branch_name"] = args.branch_name
        param_dict["platform"] = args.platform
        param_dict["check_type"] = args.check_type
        param_dict["commit_id"] = args.commit_id
        param_dict[
            "static_check_result_endpoint"
        ] = "http://10.250.67.31:8080/qat-api/api/v2/static/result"
        param_dict[
            "unittest_check_result_endpoint"
        ] = "http://10.250.67.31:8080/qat-api/api/v2/static/code"
        param_dict["pipeline_link"] = args.pipeline_link
        param_dict["report_link"] = args.report_link

        # scan_forbidden_functions 的参数
        param_dict["path"] = args.path
        param_dict["keywords"] = args.forbidden_functions
        param_dict["filter_path"] = args.filter_path_keywords
        param_dict["check_fun_key_words_path"] = args.check_fun_key_words_path
        param_dict["scan_allow_list_file"] = args.scan_allow_list_file
        param_dict["check_specified_file_path"] = args.check_specified_file_info.split(
            ","
        )[0]
        try:
            param_dict[
                "check_specified_file_exit"
            ] = args.check_specified_file_info.split(",")[1]
        except Exception:
            param_dict["check_specified_file_exit"] = "false"  # 如果没有给值，默认不符合要求时，不退出
        # sonarqube的参数
        param_dict["QualityGateStatus"] = args.QualityGateStatus
        param_dict["threshold_info"] = args.threshold_info
        # parasoft的参数
        param_dict["urls"] = args.urls
        param_dict["p0_threshold"] = int(args.p0_threshold)
        param_dict["p1_threshold"] = int(args.p1_threshold)
        # unittest_and_coverage 的参数
        param_dict["unittest_log_path"] = args.unittest_log_path
        param_dict["coverage_log_path"] = args.coverage_log_path
        logging.info("param_dict={}".format(param_dict))
        return param_dict

    @staticmethod
    def post_to_backend(post_json, endpoint):
        """将信息传给后端
        :param post_json:
        :param endpoint:
        :return:
        """
        max_try_num = 10
        while max_try_num > 0:
            try:
                res = requests.post(endpoint, json=post_json, timeout=30)
                res.raise_for_status()
                logging.info(res.json())
            except Exception as e:
                logging.error("* * Post failed: " + str(e))
                max_try_num -= 1
                time.sleep(1)
                continue
            break

    def _get_module_project_name(self, param_dict):
        """根据外部信息，从csv中获取模块名与项目名
        :author:             zhangwei
        :date:               20211022
        :param param_dict:  从外部传入的信息
        :return:   （str）first_module_name, second_module_name, project_name
        """
        repo_branch_name = "{}_{}".format(
            param_dict["repo_name"], param_dict["branch_name"]
        )
        if repo_branch_name not in param_dict["name_dict"].keys():
            # 如果在csv文件中，查不到repo_branch_name，则给出一些默认值
            logging.error("{} not in name_dict_info.csv!!!".format(repo_branch_name))
            first_module_name = "-"
            second_module_name = param_dict["repo_name"]
            project_name = "TianMaShan-L"
            continue_on_error = self.continueOnError
        else:
            # 从csv文件中，获取模块名与项目名
            first_module_name = param_dict["name_dict"][repo_branch_name][
                "first_module_name"
            ]
            second_module_name = param_dict["name_dict"][repo_branch_name][
                "second_module_name"
            ]
            project_name = param_dict["name_dict"][repo_branch_name]["project_name"]
            continue_on_error = param_dict["name_dict"][repo_branch_name][
                "continueOnError"
            ]
        return first_module_name, second_module_name, project_name, continue_on_error

    def _upload_dict(self, param_dict, result, threshold, report_link, info=None):
        """上传静态扫描的信息给后端
        :author:             zhangwei
        :date:               20211013
        :param param_dict: 从外部传入的信息
        :param result:     检查成功与失败的信息
        :param threshold:  阈值
        :param report_link: 检查报告的链接
        :param info:       检查类别，方便打印日志，区分检查
        :return:
        """
        # 整合所有信息，传给后端
        (
            first_module_name,
            second_module_name,
            project_name,
            continue_on_error,
        ) = self._get_module_project_name(param_dict)
        res_dict = {
            "first_module_name": first_module_name,
            "second_module_name": second_module_name,
            "project_name": project_name,
            "repo_name": param_dict["repo_name"],
            "branch_name": param_dict["branch_name"],
            "platform": param_dict["platform"],
            "check_type": param_dict["check_type"],
            "commit_id": param_dict["commit_id"],
            "continueOnError": continue_on_error,
            "result": result,
            "threshold": threshold,
            "report_link": report_link,
        }
        logging.info("* * Post static code check result:{}".format(res_dict))
        # todo 暂时不上传
        # self.post_to_backend(post_json=res_dict, endpoint=param_dict["static_check_result_endpoint"])
        if (result == self.failed) and (continue_on_error != "TRUE"):
            self.except_exit(info="{} failed, please check pipeline!!!".format(info))

    def _execut_scan_forbidden_functions(
        self, result, threshold, report_link, param_dict
    ):
        """执行scan_forbidden_functions，并获取扫描结果
        :author:             zhangwei
        :date:               20211013
        :param result:       扫描结果
        :param threshold:    阈值
        :param report_link:  报告的链接
        :param param_dict:   从外部获取的参数
        :return:
        """
        try:
            # todo 记得改为scan_forbidden_functions
            import scan_forbidden_functions_20211103 as scan_forbidden_functions

            # 1. 执行scan_forbidden_functions
            exp_value, act_value = scan_forbidden_functions.check_main(param_dict)
            # 重新赋值
            threshold = "exp: {}, act: {}".format(exp_value, act_value)
            result = self.failed if int(act_value) > int(exp_value) else self.success
            report_link = param_dict["report_link"]
        except Exception as e:
            # 2. 有异常时，重新定义
            threshold = "exp: None, act: None"
            result = self.failed
            report_link = param_dict["pipeline_link"]
            logging.error("* * execut scan_forbidden_functions failed: {}".format(e))
        finally:
            # 3. 无论成功失败，都将结果上传给后端
            self._upload_dict(
                param_dict,
                result,
                threshold,
                report_link,
                info="scan_forbidden_functions",
            )

    def _execut_sonarqube(self, result, threshold, report_link, param_dict):
        """获取sonarqube的执行结果
        :author:             zhangwei
        :date:               20211013
        :param result:     执行结果的初始值
        :param threshold:  阈值
        :param report_link: 报告的链接
        :param param_dict:  从外部获取的参数
        :return:
        """
        try:
            # 1. 将外部信息，传入变量
            if "OK" in param_dict["QualityGateStatus"]:
                result = self.success
            else:
                result = self.failed
            # 过滤掉有null的情况
            threshold_tmp = []
            for item in param_dict["threshold_info"].split(","):
                if "null" not in item:
                    threshold_tmp.append(item)
                continue
            threshold = ",".join(str(p) for p in threshold_tmp)
            report_link = param_dict["report_link"]
        except Exception as e:
            # 2. 有异常时，重新定义
            threshold = "exp: None, act: None"
            result = self.failed
            report_link = param_dict["pipeline_link"]
            logging.error("* * execut sonarqube_check failed: {}".format(e))
        finally:
            # 3. 无论成功失败，都将结果上传给后端
            self._upload_dict(
                param_dict, result, threshold, report_link, info="sonarqube_check"
            )

    def _execut_parasoft(self, result, threshold, report_link, param_dict, type_info):
        """获取parasoft的执行结果
        :author:             zhangwei
        :date:               20211013
        :param result:    执行结果的初始值
        :param threshold: 阈值
        :param report_link: 报告的链接
        :param param_dict: 从外部获取的参数
        :param type_info:  parasoft的检查类别
        :return:
        """
        try:
            # todo 改为 analyze_parasoft_report
            import analyze_parasoft_report_20211103 as analyze_parasoft_report

            # 1.执行analyze_parasoft_report
            obj_parasoft = analyze_parasoft_report.AnalyzeReport()
            url_list = param_dict["urls"].split(",")
            # 获取对应type_info的url
            for url_tmp in url_list:
                if type_info in url_tmp:
                    logging.info("*********url={}".format(url_tmp))
                    param_dict["url"] = url_tmp
            if "url" not in param_dict.keys():
                threshold = "exp: None, act: url_is_empty"
                result = self.failed
                logging.error("type_info={}, url is empty ".format(type_info))
            else:
                # 获取到正确url后，再进行报告的分析
                p0_num, p1_num = obj_parasoft.analyze_parasoft_report(para_dict)
                # 重新赋值
                threshold = "exp_p0: {}, act_p0: {}, exp_p1: {}, act_p1: {}".format(
                    param_dict["p0_threshold"],
                    p0_num,
                    param_dict["p1_threshold"],
                    p1_num,
                )
                if (
                    (p0_num > param_dict["p0_threshold"])
                    or (p1_num > param_dict["p1_threshold"])
                    or (p0_num == "none")
                    or (p1_num == "none")
                ):
                    result = self.failed
                else:
                    result = self.success
            report_link = param_dict["report_link"]
        except Exception as e:
            # 2. 有异常时，重新定义
            threshold = "exp: None, act: None"
            result = self.failed
            report_link = param_dict["pipeline_link"]
            logging.error("* * execut parasoft_check failed: {}".format(e))
        finally:
            # 3.无论成功失败，都将结果上传给后端
            self._upload_dict(
                param_dict, result, threshold, report_link, info="parasoft"
            )

    def _execut_unittest_and_coverage(self, param_dict):
        """获取unittest与coverage的执行结果
        :author:             zhangwei
        :date:               20211021
        :param param_dict: 从外部获取的参数
        :return:
        """
        logging.info("check_type={}".format(param_dict["check_type"]))
        # 1. 给结果赋予初始值，避免传给后端空
        case_num, case_pass_num, case_pass_rate = "none", "none", "none"
        lines, functions, branches = "none", "none", "none"
        report_link = "none"
        try:
            # 2. 解析单元测试的结果
            if ("unittest" in param_dict["check_type"]) and (
                param_dict["unittest_log_path"] != ""
            ):
                (
                    case_num,
                    case_pass_num,
                    case_pass_rate,
                ) = self._analytical_unittest_info(param_dict)
            elif ("unittest" in param_dict["check_type"]) and (
                param_dict["unittest_log_path"] == ""
            ):
                case_num, case_pass_num, case_pass_rate = "none", "none", "none"
            # 3. 解析代码覆盖率的结果
            if ("coverage" in param_dict["check_type"]) and (
                param_dict["coverage_log_path"] != ""
            ):
                lines, functions, branches = self._analytical_coverage_info(param_dict)
            elif ("coverage" in param_dict["check_type"]) and (
                param_dict["coverage_log_path"] == ""
            ):
                lines, functions, branches = "none", "none", "none"
            report_link = param_dict["report_link"]
        except Exception as e:
            # 4. 有异常时，重新定义
            logging.error("* * execut unittest_and_coverage failed: {}".format(e))
            case_num, case_pass_num, case_pass_rate = "none", "none", "none"
            lines, functions, branches = "none", "none", "none"
            report_link = param_dict["pipeline_link"]
        finally:
            # 5. 整合所有信息，传给后端
            (
                first_module_name,
                second_module_name,
                project_name,
                continue_on_error,
            ) = self._get_module_project_name(param_dict)
            res_dict = {
                "first_module_name": first_module_name,
                "second_module_name": second_module_name,
                "project_name": project_name,
                "repo_name": param_dict["repo_name"],
                "branch_name": param_dict["branch_name"],
                "platform": param_dict["platform"],
                "commit_id": param_dict["commit_id"],
                "case_number": case_num,
                "case_pass_number": case_pass_num,
                "case_pass_rate": str(case_pass_rate),
                "line_cover": lines,
                "function_cover": functions,
                "branches_cover": branches,
                "report_link": report_link,
            }
            logging.info("* * Post unittest and coverage result:{}".format(res_dict))
            # todo 暂时不上传
            # self.post_to_backend(post_json=res_dict, endpoint=param_dict["unittest_check_result_endpoint"])
            if continue_on_error != "TRUE":
                if (lines == "none") or (functions == "none") or (branches == "none"):
                    self.except_exit(
                        info="{} failed, please check pipeline!!!".format(
                            "unittest_and_coverage"
                        )
                    )
                else:
                    line_num = int(lines.split("%")[0])
                    functions = int(functions.split("%")[0])
                    branches = int(branches.split("%")[0])
                    if (line_num < 0) or (functions < 0) or (branches < 0):
                        self.except_exit(
                            info="{} failed, lines={}, functions={}, branches={}!!!"
                            "".format(
                                "unittest_and_coverage", line_num, functions, branches
                            )
                        )

    @staticmethod
    def _analytical_unittest_info(param_dict):
        """分析单元测试结果的信息
        :author:             zhangwei
        :date:               20211021
        :param param_dict:   从外部获取的信息
        :return:
        """
        logging.info("analytical_unittest_info begin")
        case_num_key = "[==========] Running"
        case_pass_num = 0
        case_pass_key = "[       OK ]"
        case_num = 1
        with open(param_dict["unittest_log_path"], "r", encoding="utf-8") as f:
            for line in f.readlines():
                if case_num_key in line:
                    logging.info("case_num_line={}".format(line))
                    if "tests from" in line:
                        case_num = int(
                            line.split(case_num_key)[1].split("tests from")[0].strip()
                        )
                    else:
                        case_num = int(
                            line.split(case_num_key)[1].split("test from")[0].strip()
                        )
                    logging.info("case_num: {}".format(case_num))
                if case_pass_key in line:
                    case_pass_num = case_pass_num + 1
            logging.info("case_pass_num: {}".format(case_pass_num))
            case_pass_rate = "{:.1%}".format(round(case_pass_num / case_num, 4))
            logging.info("case_pass_rate: {}".format(case_pass_rate))
        return case_num, case_pass_num, case_pass_rate

    @staticmethod
    def _analytical_coverage_info(param_dict):
        """分析代码覆盖率结果的信息
        :author:             zhangwei
        :date:               20211021
        :param param_dict:   从外部获取的信息
        :return:
        """
        logging.info("analytical_coverage_info begin")
        key_i = 0
        lines = "none"
        functions = "none"
        branches = "none"
        with open(param_dict["coverage_log_path"], "r", encoding="utf-8") as f_logs:
            for i, line in enumerate(f_logs):
                if "Overall coverage rate:\n" == line:
                    key_i = i
                    break
            if key_i == 0:
                logging.error("find info[Overall coverage rate] failed")
            else:
                log_content_list = f_logs.readlines()
                logging.info("log_content_list={}".format(log_content_list))
                for log_i in log_content_list:
                    if "lines" in log_i:
                        lines = log_i.strip().split(":")[1].split("(")[0].strip()
                    elif "functions" in log_i:
                        functions = log_i.strip().split(":")[1].split("(")[0].strip()
                    elif "branches" in log_i:
                        branches = log_i.strip().split(":")[1].split("(")[0].strip()
        logging.info("lines={}".format(lines))
        logging.info("functions={}".format(functions))
        logging.info("branches={}".format(branches))
        return lines, functions, branches

    def upload_to_qat(self, param_dict):
        # 1.定义初始值
        result = "none"
        threshold = None
        report_link = None
        # 2.根据不同类别，执行检查，获取需要的信息，并上传结果给后端
        if param_dict["check_type"] == "scan_forbidden_functions":
            # 下载必要的文件
            link_lst = [
                "http://10.3.21.11:6959/sonarqube/check_fun_key_word.txt",
                "http://10.3.21.11:6959/sonarqube/scan_forbidden_functions_20211103.py",
            ]
            if param_dict["scan_allow_list_file"] != "":
                link_lst.append(
                    "http://10.3.21.11:6959/sonarqube/scan_allow_list/{}"
                    "".format(param_dict["scan_allow_list_file"].strip())
                )
            self.wget_file(link_lst)
            # 执行检查
            self._execut_scan_forbidden_functions(
                result, threshold, report_link, param_dict
            )
        elif param_dict["check_type"] == "sonarqube":
            self._execut_sonarqube(result, threshold, report_link, param_dict)
        elif param_dict["check_type"] == "autosar":
            self._execut_parasoft(
                result, threshold, report_link, param_dict, type_info="autosar"
            )
        elif param_dict["check_type"] == "metrics":
            self._execut_parasoft(
                result, threshold, report_link, param_dict, type_info="metrics"
            )
        elif ("unittest" in param_dict["check_type"]) or (
            "coverage" in param_dict["check_type"]
        ):
            self._execut_unittest_and_coverage(param_dict)


if __name__ == "__main__":
    obj = UploadToQAT()
    logging.info("\t 【0. wget file】")
    link_lst = [
        "http://10.3.21.11:6959/sonarqube/name_dict_info_20211103.csv",
        "http://10.3.21.11:6959/parasoft/check_code/analyze_parasoft_report_20211103.py",
    ]
    obj.wget_file(link_lst)
    logging.info("\t 【1. analytical_parameters】")
    para_dict = obj.analytical_parameters()
    name_dict = obj.create_name_dict()  # 生成repo_分支名，与第一模块名、第二模块名、项目名的对应关系
    para_dict["name_dict"] = name_dict
    logging.info("\t 【2. executing check scripts and upload info to QAT】")
    obj.upload_to_qat(para_dict)
