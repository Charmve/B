# BenchRT

BenchRT means benchmarking regression testting or benchmark runtime in real-world device.

## Features

- QBuild: provide cross-platform run-time pipeline
- Support cross-platform, multi-platform
- Automated testing at scale
- Report automated make, alter

## Quick start

```
./scripts/start_cross_compile_docker.sh --project j5 --office suzhou
./scripts/goto_cross_compile_docker.sh --project j5

qbuild --init

qbuild --help
# eg:qbuild --benchmark j5 onboard/logging/logging_bm
```

[![image](https://user-images.githubusercontent.com/29084184/219936570-c25ed0d4-f588-4e43-bcb7-f5597e7e5ba0.png)](https://asciinema.org/a/k0rFmkO8EZCwn6hj8KEzZuCzL)

演示链接：https://asciinema.org/a/k0rFmkO8EZCwn6hj8KEzZuCzL

## Usage

### qbuild

```bash
charmve@SZ-zhangwei:/charmve$ qbuild --help
🚀 Welcome to use QBuild!

USAGE:
    qbuild <command> [options] [<arguments...>]

VERSION:
    1.0.0

OPTIONS:
    -i, --init              Make qbuild init
    -b, --build             Build module, include unit test, benchmark single
                            module and mutil-module
    -it, --install          Make module package
    -c, --connect           Connect to target platform easy, include real env and virtual env
    -d, --deploy            Deploy module binary
    -r, --run               Run module binary in mutil-platform
    -u, --update            Update the sysroot by manaul
    -f, --format            Format code in X-Comipler docker
    -p, --pull              Pull file from arm-platform to local, like module 
                            library or config file
    -t, --test              Test module (only for qbuild SDEer)
    -ut, --unittest         Debug unit test
    -bm, --benchmark        Run benchmark to get report
    -pf, --perf             Perf module performance
    -co, --coverage         Give the coverage report in target platform
    -sc, --sonarqube        Source code static analysis and security scan
    -is, --issues           Pull issues about Qbuild to Onboard Infra
    -cl, --clean            Clean QBuild cache
    -v, --version           QBuild's version
    -h, --help              Show this message and exit

Run 'qbuild COMMAND' for more information on a command.

Visit https://qcraft.feishu.cn/docx/Vo6GdVCDqow0v5xX5RkcxBTXnQb to get more information and push issues.
```

结果展示：

onboard/lite 路径下 单元测试结果

![image](https://user-images.githubusercontent.com/29084184/219936651-ed6d306e-b789-44d5-9a48-0fe31f545ff7.png)

### bench-rt

```bash
cd BenchRT
nohup python3 -m http.server >>/dev/null &
export PATH=$PATH:$(pwd)/google-cloud-sdk/bin

bazel run :benchmark -- --bazel_commits=fffc26b5cc1bbe6c977af9971ed21e2e3d275d28,25be21130ba774e9f02cc39a010aafe64a3ab245 --project_source=/charmve/ --project_commits=6dd9685b9e --data_directory=/tmp/bazel-bench-data --verbose --platform=x86 --project_label=dev-test  --collect_profile=True --aggregate_json_profiles=True -- run  --verbose_failures //qbuild/examples/helloworld:helloworld

bazel run :benchmark -- --bazel_commits=fffc26b5cc1bbe6c977af9971ed21e2e3d275d28,25be21130ba774e9f02cc39a010aafe64a3ab245 --project_source=/charmve/ --project_commits=6dd9685b9e --platform=x86 --project_label=dev-test  -- run  --verbose_failures //onboard/math:vec_bm

bazel run :benchmark -- --bazel_commits=fffc26b5cc1bbe6c977af9971ed21e2e3d275d28,25be21130ba774e9f02cc39a010aafe64a3ab245 --project_source=/charmve/ --project_commits=6dd9685b9e --platform=$1 --project_label=dev-test  -- run  --verbose_failures onboard/math/fast_math_bm


bazel run report:generate_report --  --storage_bucket=0.0.0.0:8000/bazel-bench/bazel-bench-data --project=bazel-bench-test

```

结果展示：

- x86-有对应bm：

![image](https://user-images.githubusercontent.com/29084184/219936292-56333dba-14fb-4436-a175-f4bb97c097d0.png)

![image](https://user-images.githubusercontent.com/29084184/219936285-5ce45b39-e1f3-47e4-b396-c31aeee3df47.png)


- x86-无对应bm：

pre-run一次，再统计连续跑5次作为最终结果。

![image](https://user-images.githubusercontent.com/29084184/219936283-80244727-c66d-434f-99d1-981da7f57098.png)

![image](https://user-images.githubusercontent.com/29084184/219936274-b9181d66-78ec-4514-8ec3-1c80baca30c9.png)


收集汇总所有的json-profile文件：
``bazel run :benchmark -- --bazel_commits=fffc26b5cc1bbe6c977af9971ed21e2e3d275d28,25be21130ba774e9f02cc39a010aafe64a3ab245 --project_source=/qcraft/ --project_commits=6dd9685b9e --platform=x86 --project_label=dev-test  --collect_profile=True --aggregate_json_profiles=True -- run  --verbose_failures //qbuild/examples/hiqcraft:hiqcraft``

- j5-有对应bm：

qbuild --run <platform>

![image](https://user-images.githubusercontent.com/29084184/219936266-7496818d-768f-48c4-b896-f1591ded519e.png)


j5-无对应bm：

![image](https://user-images.githubusercontent.com/29084184/219936257-0c61d4a9-c718-4cf1-957f-bef3c07d7550.png)


## Profiling

[Build performance metrics](https://blog.bazel.build/2022/11/15/build-performance-metrics.html)

![image](https://user-images.githubusercontent.com/29084184/219936441-85e68619-8f29-433e-90d3-c0f8d457ef8f.png)


## Setup runtime environment

docs: docs/ARM64编译环境搭建-以J5为例.docx


### multi-platform switch 'goto x' 
```
sudo cat >> "$HOME/.bashrc" << EOF

function goto() {
 platform=$1
 cd ~/charmve
 
 existing_running_docker=("$(docker ps --filter name="charmve")")
 if [ $platform == j5 ] || [ $platform == orin ]; then
    if [[ " ${existing_running_docker[*]} " =~ cross_compile_[j5,orin] ]]; then
        ./scripts/goto_cross_compile_docker.sh --project $platform
    else
        ./scripts/start_cross_compile_docker.sh --project $platform --office suzhou
        ./scripts/goto_cross_compile_docker.sh --project $platform
    fi
 elif [ $platform == x86 ]; then
    if [[ " ${existing_running_docker[*]} " =~ dev_charmve ]]; then
        ./scripts/goto_dev_docker.sh
    else
        ./scripts/start_dev_docker.sh --office suzhou
        ./scripts/goto_dev_docker.sh
    fi
 elif [ $platform == j5_v ]; then
    docker exec -it j5 bash
 else
    echo "goto j5/j5_v/orin/x86"
    # exit 0
 fi
}

EOF

source $HOME/.bashrc

```

### setup virtual hb-j5 environment
 
``
docker build -t charmve/j5-bionic-qemu-20221230_0011:v1 -f dev/j5-qemu.aarch64.dockerfile 
``

