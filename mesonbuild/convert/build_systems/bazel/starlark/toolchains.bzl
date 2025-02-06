# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Authors

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("@bazel_tools//tools/cpp:unix_cc_toolchain_config.bzl", "cc_toolchain_config")
load("@rules_cc//cc:defs.bzl", "cc_toolchain")

def _meson_repos_impl(ctx):
    for mod in ctx.modules:
        for repo in mod.tags.repo:
            kwargs = {
                "name": repo.name,
                "url": repo.url,
                "sha256": repo.sha256,
            }
            if repo.build_file:
                kwargs["build_file"] = repo.build_file
            if repo.build_file_content:
                kwargs["build_file_content"] = repo.build_file_content
            if repo.type:
                kwargs["type"] = repo.type
            http_archive(**kwargs)

repo_tag = tag_class(
    attrs = {
        "name": attr.string(mandatory = True),
        "url": attr.string(mandatory = True),
        "sha256": attr.string(mandatory = True),
        "build_file": attr.string(),
        "build_file_content": attr.string(),
        "type": attr.string(),
    },
)

meson_repos = module_extension(
    implementation = _meson_repos_impl,
    tag_classes = {"repo": repo_tag},
)

def define_meson_toolchain(name, cpu, target_system_name, tool_paths, sysroot_repo, fuchsia_cpu):
    workspace_name = Label(sysroot_repo + "//:all").workspace_name
    sysroot_path = "external/" + workspace_name + "/arch/" + fuchsia_cpu + "/sysroot"

    cc_toolchain_config(
        name = name + "_config",
        cpu = cpu,
        compiler = "gcc",
        toolchain_identifier = name,
        host_system_name = "local",
        target_system_name = target_system_name,
        target_libc = "unknown",
        abi_version = "unknown",
        abi_libc_version = "unknown",
        builtin_sysroot = sysroot_path,
        cxx_builtin_include_directories = [
            ".",
            sysroot_path + "/include",
        ],
        compile_flags = [
            "-target",
            target_system_name,
            "-no-canonical-prefixes",
            "--sysroot",
            sysroot_path,
        ],
        link_flags = [
            "-target",
            target_system_name,
            "-no-canonical-prefixes",
            "--sysroot",
            sysroot_path,
        ],
        tool_paths = tool_paths,
    )

    cc_toolchain(
        name = name + "_cc_toolchain",
        all_files = ":all_files",
        compiler_files = ":all_files",
        dwp_files = ":empty",
        linker_files = ":all_files",
        objcopy_files = ":all_files",
        strip_files = ":all_files",
        toolchain_config = ":" + name + "_config",
        supports_param_files = 0,
    )
