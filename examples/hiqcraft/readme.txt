# QBuild example

## Usage:

bazel run -c opt --copt -D__DRIVE_ORIN__ qbuild/examples/hiqcraft/hiqcraft

bazel build -c opt --copt -D__X86_64__ qbuild/examples/hiqcraft/hiqcraft
bazel build -c opt --copt -D__X9HP__ qbuild/examples/hiqcraft/hiqcraft
bazel build -c opt --copt -D__J5__ qbuild/examples/hiqcraft/hiqcraft

## QBuild

qbuild --build x9hp qbuild/examples/hiqcraft/hiqcraft
qbuild --build j5 qbuild/examples/hiqcraft/hiqcraft
qbuild --deploy x9hp bazel-bin/qbuild/examples/hiqcraft/hiqcraft
qbuild --run x9hp qbuild/examples/hiqcraft/hiqcraftt
qbuild --benchmark x9hp onboard/logging/logging_bm
qbuild --unittest x9hp onboard/logging/stf_reader_writer_test


