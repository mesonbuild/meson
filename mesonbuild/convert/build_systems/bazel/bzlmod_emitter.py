#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import os
import shutil

from mesonbuild.mesonlib import MachineChoice
from mesonbuild.convert.build_systems.common import ConvertStateTracker
from mesonbuild.convert.build_systems.bazel.state import BazelBackend

BAZEL_MODULE_TEMPLATE = """\
module(name = "{project_name}", version = "1.0")

bazel_dep(name = "rules_cc", version = "0.2.17")
bazel_dep(name = "platforms", version = "1.0.0")
bazel_dep(name = "rules_license", version = "1.0.0")
bazel_dep(name = "rules_python", version = "1.7.0")

meson_repos = use_extension("//bazel:toolchains.bzl", "meson_repos")

{extension_usage}

{use_repos}

{register_toolchains}

{python_setup}
"""

PYTHON_MODULE_SETUP_TEMPLATE = """\
python = use_extension("@rules_python//python/extensions:python.bzl", "python")
python.toolchain(
    python_version = "3.10",
    is_default = True,
)

pip = use_extension("@rules_python//python/extensions:pip.bzl", "pip")
pip.parse(
    hub_name = "meson_python_deps",
    python_version = "3.10",
    requirements_lock = "//bazel:requirements.txt",
)

use_repo(pip, "meson_python_deps")
"""

EXTENSION_TOOLCHAIN_TAG_TEMPLATE = """\
meson_repos.repo(
    name = "{name}",
    url = "{url}",
    sha256 = "{sha256}",
    build_file = "{build_file}",
    type = "{file_type}",
)
"""

EXTENSION_SYSROOT_TAG_TEMPLATE = """\
meson_repos.repo(
    name = "{name}",
    url = "{url}",
    sha256 = "{sha256}",
    build_file_content = 'filegroup(name = "all_files", srcs = glob(["**"]), visibility = ["//visibility:public"])',
    type = "zip",
)
"""

EXTENSION_GENERAL_TAG_TEMPLATE = """\
meson_repos.repo(
    name = "{name}",
    url = "{url}",
    sha256 = "{sha256}",
)
"""

COMPILER_MAPPING_TEMPLATE = """\
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "compiler_files",
    srcs = glob(["**/*"]),
)

filegroup(
    name = "all_files",
    srcs = [":compiler_files"] + {sysroot_files},
)

filegroup(name = "empty")

load("@//bazel:toolchains.bzl", "define_meson_toolchain")

define_meson_toolchain(
    name = "{name}",
    cpu = "{cpu}",
    target_system_name = "{target_system_name}",
    tool_paths = {{
        {tool_paths}
    }},
    sysroot_repo = "{sysroot_repo}",
    fuchsia_cpu = "{fuchsia_cpu}",
)
"""

TOOLCHAINS_BUILD_TEMPLATE = """\
toolchain(
    name = "{name}_toolchain",
    target_compatible_with = [
        "@platforms//cpu:{cpu}",
        "@platforms//os:{os}",
    ],
    toolchain = "@{name}//:{name}_cc_toolchain",
    toolchain_type = "@bazel_tools//tools/cpp:toolchain_type",
)
"""

PLATFORMS_BUILD_TEMPLATE = """\
package(default_visibility = ["//visibility:public"])

platform(
    name = "{name}_platform",
    constraint_values = [
        "@platforms//cpu:{cpu}",
        "@platforms//os:{os}",
    ],
)
"""


def _emit_python_requirements(output_dir: str,
                              state_tracker: ConvertStateTracker) -> bool:  # fmt: skip
    python_libraries = state_tracker.project_config.dependencies.python_libraries
    if not python_libraries:
        return False

    bazel_dir = os.path.join(output_dir, "bazel")
    os.makedirs(bazel_dir, exist_ok=True)

    content = ""
    for dep, version in sorted(python_libraries.items()):
        content += f"{dep}=={version}\n"

    with open(os.path.join(bazel_dir, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write(content)

    # Ensure bazel/ is a package
    with open(os.path.join(bazel_dir, "BUILD.bazel"), "w", encoding="utf-8") as f:
        f.write("")

    return True


def _emit_toolchains_and_platforms(
        output_dir: str,
        state_tracker: ConvertStateTracker,
        copyright_string: str) -> T.Tuple[T.List[str], T.List[str], T.List[str]]:  # fmt: skip
    backend = T.cast(BazelBackend, state_tracker.backend)
    extension_usage: T.List[str] = []
    register_toolchains: T.List[str] = []
    repos: T.List[str] = []

    for dep in sorted(list(backend.external_deps), key=lambda x: x.repo):
        extension_usage.append(
            EXTENSION_GENERAL_TAG_TEMPLATE.format(
                name=dep.repo,
                url=dep.source_url,
                sha256=dep.source_hash or "",
            )
        )
        repos.append(f'"{dep.repo}"')

    toolchains_with_wrap = [
        tc for tc in state_tracker.all_toolchains if tc.compilers_wrap
    ]
    if not toolchains_with_wrap:
        return (extension_usage, register_toolchains, repos)

    toolchains_build_content = copyright_string + "\n"
    toolchains_build_content += 'filegroup(name = "empty")\n\n'
    platforms_build_content = copyright_string + "\n"

    toolchains_dir = os.path.join(output_dir, "bazel", "toolchains")
    platforms_dir = os.path.join(output_dir, "bazel", "platforms")
    os.makedirs(toolchains_dir, exist_ok=True)
    os.makedirs(platforms_dir, exist_ok=True)

    for tc in toolchains_with_wrap:
        compilers_wrap = tc.compilers_wrap
        name = tc.name
        extension_usage.append(
            EXTENSION_TOOLCHAIN_TAG_TEMPLATE.format(
                name=name,
                url=compilers_wrap.url,
                sha256=compilers_wrap.sha256 or "",
                build_file=f"//bazel/toolchains:{name}_compiler.BUILD",
                file_type="zip",
            )
        )
        register_toolchains.append(
            f'register_toolchains("//bazel/toolchains:{name}_toolchain")'
        )
        repos.append(f'"{name}"')

        sysroot_files = "[]"
        if tc.sysroot_wrap:
            sysroot_name = f"{name}_sysroot"
            sysroot_wrap = tc.sysroot_wrap
            extension_usage.append(
                EXTENSION_SYSROOT_TAG_TEMPLATE.format(
                    name=sysroot_name,
                    url=sysroot_wrap.url,
                    sha256=sysroot_wrap.sha256 or "",
                )
            )
            sysroot_files = f'["@{sysroot_name}//:all_files"]'
            repos.append(f'"{sysroot_name}"')

        binaries = compilers_wrap.binaries
        # Extract all available tools for tool_paths
        tool_mapping = [
            ("gcc", ["ccc", "gcc", "cc"]),
            ("cpp", ["cpp"]),
            ("ld", ["ld"]),
            ("ar", ["ar"]),
            ("nm", ["nm"]),
            ("objcopy", ["objcopy"]),
            ("objdump", ["objdump"]),
            ("gcov", ["gcov"]),
            ("strip", ["strip"]),
            ("as", ["as"]),
        ]

        tool_paths_items = []
        for bazel_name, toml_names in tool_mapping:
            for toml_name in toml_names:
                if toml_name in binaries:
                    tool_paths_items.append(f'"{bazel_name}": "{binaries[toml_name]}"')
                    break

        tool_paths_str = ",\n        ".join(tool_paths_items)

        machine_info = tc.machine_info[MachineChoice.HOST]
        cpu = machine_info.cpu_family
        os_name = machine_info.system

        # Fuchsia uses 'x64' and 'arm64' in its SDK paths
        fuchsia_cpu = cpu
        if cpu == "x86_64":
            fuchsia_cpu = "x64"
        elif cpu == "aarch64":
            fuchsia_cpu = "arm64"

        # Bzlmod Resolution:
        # We use stable names and resolve actual paths in the define_meson_toolchain macro.
        sysroot_repo = f"@{name}_sysroot" if tc.sysroot_wrap else ""

        # Standard Fuchsia Triple
        target_triple = f"{cpu}-fuchsia"

        with open(
            os.path.join(toolchains_dir, f"{name}_compiler.BUILD"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(
                COMPILER_MAPPING_TEMPLATE.format(
                    name=name,
                    cpu=cpu,
                    os=os_name,
                    target_system_name=target_triple,
                    tool_paths=tool_paths_str,
                    sysroot_files=sysroot_files,
                    sysroot_repo=sysroot_repo,
                    fuchsia_cpu=fuchsia_cpu,
                )
            )

        toolchains_build_content += TOOLCHAINS_BUILD_TEMPLATE.format(
            name=name,
            cpu=machine_info.cpu_family,
            os=machine_info.system,
        )
        platforms_build_content += PLATFORMS_BUILD_TEMPLATE.format(
            name=name,
            cpu=machine_info.cpu_family,
            os=machine_info.system,
        )

    with open(os.path.join(toolchains_dir, "BUILD.bazel"), "w", encoding="utf-8") as f:
        f.write(toolchains_build_content)

    with open(os.path.join(platforms_dir, "BUILD.bazel"), "w", encoding="utf-8") as f:
        f.write(platforms_build_content)

    return (extension_usage, register_toolchains, repos)


def _emit_bazel_rules(output_dir: str) -> None:
    bazel_dir = os.path.join(output_dir, "bazel")
    os.makedirs(bazel_dir, exist_ok=True)

    # Ensure bazel/ BUILD.bazel exists
    build_file = os.path.join(bazel_dir, "BUILD.bazel")
    if not os.path.exists(build_file):
        with open(build_file, "w", encoding="utf-8") as f:
            f.write("")

    shutil.copy(
        os.path.join(os.path.dirname(__file__), "starlark", "meson_rules.bzl"),
        os.path.join(bazel_dir, "meson_rules.bzl"),
    )


def _emit_toolchain_extension(output_dir: str) -> None:
    bazel_dir = os.path.join(output_dir, "bazel")
    os.makedirs(bazel_dir, exist_ok=True)
    shutil.copy(
        os.path.join(os.path.dirname(__file__), "starlark", "toolchains.bzl"),
        os.path.join(bazel_dir, "toolchains.bzl"),
    )


def _emit_module_bazel(
        output_dir: str,
        state_tracker: ConvertStateTracker,
        copyright_string: str) -> None:  # fmt: skip
    (extension_usage, register_toolchains, repos) = _emit_toolchains_and_platforms(
        output_dir, state_tracker, copyright_string
    )
    _emit_bazel_rules(output_dir)
    _emit_toolchain_extension(output_dir)

    python_setup = ""
    if _emit_python_requirements(output_dir, state_tracker):
        python_setup = PYTHON_MODULE_SETUP_TEMPLATE

    use_repos = "\n".join([f"use_repo(meson_repos, {r})" for r in repos])

    module_content = copyright_string + "\n"
    module_content += BAZEL_MODULE_TEMPLATE.format(
        project_name=state_tracker.project_config.project_name or "meson_project",
        extension_usage="\n".join(extension_usage),
        use_repos=use_repos,
        register_toolchains="\n".join(register_toolchains),
        python_setup=python_setup,
    )

    with open(os.path.join(output_dir, "MODULE.bazel"), "w", encoding="utf-8") as f:
        f.write(module_content)
