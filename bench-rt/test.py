import time

for i in range(10, 0, -1):
    print("\r倒计时{}秒！".format(i), end="")
    time.sleep(1)
print("\r倒计时结束！")


sum = 10  # 设置倒计时时间
interval = 0.25  # 设置屏幕刷新的间隔时间
for i in range(0, int(sum / interval)):
    list = ["\\", "|", "/", "-"]
    index = i % 4
    print("\r程序正在运行 {}".format(list[index]), end="")
    time.sleep(interval)


sum = 50  # 设置倒计时时间
interval = 0.5  # 设置屏幕刷新的间隔时间
for i in range(0, int(sum / interval) + 1):
    print(
        "\r正在加载:"
        + "|"
        + "*" * i
        + " " * (int(sum / interval) + 1 - i)
        + "|"
        + str(i)
        + "%",
        end="",
    )
    time.sleep(interval)
print("\r加载完成！")
