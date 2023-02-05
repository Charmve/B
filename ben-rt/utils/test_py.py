
import subprocess

def subprocess_popen(statement):
     p = subprocess.Popen(statement, shell=True, stdout=subprocess.PIPE)  # 执行shell语句并定义输出格式
     while p.poll() is None:  # 判断进程是否结束（Popen.poll()用于检查子进程（命令）是否已经执行结束，没结束返回None，结束后返回状态码）
         if p.wait() != 0:  # 判断是否执行成功（Popen.wait()等待子进程结束，并返回状态码；如果设置并且在timeout指定的秒数之后进程还没有结束，将会抛出一个TimeoutExpired异常。）
             print("命令执行失败，请检查设备连接状态")
             return False
         else:
             re = p.stdout.readlines()  # 获取原始执行结果
             result = []
             for i in range(len(re)):  # 由于原始结果需要转换编码，所以循环转为utf8编码并且去除\n换行
                 res = re[i].decode('utf-8').strip('\r\n')
                 result.append(res)
             return result

bazel_bin_path = subprocess_popen("which bazel")[0]
print(bazel_bin_path)


result=subprocess_popen("bazel --version | awk -F ' ' '{print $2}'")
print("====> ", result[0])

output = list(map(lambda x: x[0], result))
print("result: ", result[0], "\noutput:", output[0])


'''
import re
import requests

source = requests.get('https://www.youtube.com/c/CoinBureau/videos').text
URLs = re.findall("/watch\?v=\w*", source)
URL_IDs = list(map(lambda x: x[9:], URLs))

print(source, URLs, URL_IDs)
'''
