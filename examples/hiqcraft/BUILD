load("//bazel:rules_cc.bzl", "cc_binary")

cc_binary(
    name = "hiqcraft",
    srcs = ["hiqcraft.cc"],
    linkstatic = 1,
    visibility = ["//visibility:public"],
    deps = [
        "@boost//:context",
        "@boost//:filesystem",
        "@com_google_absl//absl/base",
        "@com_google_absl//absl/strings",
    ],
)
