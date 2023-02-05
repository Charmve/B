load("${skylib_package}lib:selects.bzl", "selects")

sh_test(
    name = "deploy_file_test",
    srcs = ["qbuild"],
    target_compatible_with = selects.with_or({
        (":foo1", ":foo2"): [":not_compatible"],
        "//conditions:default": [],
    }),
)

sh_test(
    name = "pass_on_everything_but_foo1_and_foo2",
    srcs = [":pass.sh"],
    target_compatible_with = selects.with_or({
        (":foo1", ":foo2"): [":not_compatible"],
        "//conditions:default": [],
    }),
)
