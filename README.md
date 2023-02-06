# BenchRT

BenchRT means benchmarking regression testting or benchmark runtime in real-world device.



## Features

- QBuild: provide run-time pipeline
- support cross-platform, multi-platform
- 

## Quick start

```
./scripts/start_cross_compile_docker.sh --project j5 --office suzhou
./scripts/goto_cross_compile_docker.sh --project j5

qbuild --init

qbuild --help
# eg:qbuild --benchmark j5 onboard/logging/logging_bm
```

## Usage

### qbuild

```bash
qcraft@SZ-zhangwei:/qcraft$ qbuild --help
Hello QCrafter!
USAGE:
    qbuild [options] <command> [<arguments...>]

VERSION:
    1.0.0

OPTIONS:
    -i, --init              Make qbuild init
    -b, --build             Build module, inclue unit test, benchmark single
                            module and mutil-module
    -c, --connect           Connect to target platform easy
    -d, --deploy            Deploy module binary
    -r, --run               Run module binary in mutil-platform
    -u, --update            Update the sysroot by manaul
    -f, --format            Format code in X-Comipler docker
    -p, --pull              Pull file from arm-platform to local, like module
                            library or config file
    -t, --test              Test module(only for qbuild SDEer)
    -ut, --unittest         Debug unit test
    -bm, --benchmark        Run benchmark to get report
    -is, --issues           Pull issues about Qbuild to Onboard Infra
    -co, --coverage         Give the coverage report in target platform
    -sc, --sonarqube        Source code static analysis and security scan
    -v, --version           QBuild's version
    -h, --help              Show this message and exit
```


### bench-rt

cd bench-rt
nohup python3 -m http.server >>/dev/null &
export PATH=$PATH:$pwd/google-cloud-sdk/bin

bazel run :benchmark -- --bazel_commits=fffc26b5cc1bbe6c977af9971ed21e2e3d275d28,25be21130ba774e9f02cc39a010aafe64a3ab245 --project_source=/qcraft/ --project_commits=6dd9685b9e --data_directory=/tmp/bazel-bench-data --verbose --platform=x86 --project_label=dev-test  --collect_profile=True --aggregate_json_profiles=True -- run  --verbose_failures //qbuild/examples/hiqcraft:hiqcraft

bazel run report:generate_report --  --storage_bucket=0.0.0.0:8000/bench-rt/bazel-bench-data --project=bazel-bench-data



## Setup runtime environment
docs: https://qcraft.feishu.cn/docx/X7pAdGBsloYTM5xZrIAcnmfpntg


### multi-platform switch 'goto x' 
```
sudo cat >> "$HOME/.bashrc" << EOF

function goto() {
 platform=$1
 cd ~/qcraft
 
 existing_running_docker=("$(docker ps --filter name="qcraft")")
 if [ $platform == j5 ] || [ $platform == orin ]; then
    if [[ " ${existing_running_docker[*]} " =~ cross_compile_[j5,orin] ]]; then
        ./scripts/goto_cross_compile_docker.sh --project $platform
    else
        ./scripts/start_cross_compile_docker.sh --project $platform --office suzhou
        ./scripts/goto_cross_compile_docker.sh --project $platform
    fi
 elif [ $platform == x86 ]; then
    if [[ " ${existing_running_docker[*]} " =~ dev_qcraft ]]; then
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
docker build -t qcraft/j5-bionic-qemu-20221230_0011:v1 -f j5-qemu.aarch64.dockerfile 
``
