#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
from dataclasses import dataclass
import typing as T
from pathlib import Path

from mesonbuild.mesonlib import MachineChoice
from mesonbuild.mesondata import DataFile
from mesonbuild.convert.build_systems.common import ConvertStateTracker
from mesonbuild.hermetic.common_compiler import HermeticPlatformInfo, HermeticPlatformWrap


BAZEL_MODULE_TEMPLATE = """\
module(name = "{project_name}", version = "1.0")

bazel_dep(name = "rules_cc", version = "0.2.17")
bazel_dep(name = "platforms", version = "1.0.0")
bazel_dep(name = "rules_license", version = "1.0.0")
bazel_dep(name = "rules_python", version = "1.7.0")

meson_repos = use_extension("//bazel:platforms.bzl", "meson_repos")

{extension_usage}

{use_repos}

{register_platforms}

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

EXTENSION_PLATFORM_TAG_TEMPLATE = """\
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

load("@//bazel:platforms.bzl", "define_meson_platform")

{definitions}"""

PLATFORM_DEFINITION_TEMPLATE = """\
define_meson_platform(
    name = "{name}",
    cpu = "{cpu}",
    target_system_name = "{target_system_name}",
    tool_paths = {{
        {tool_paths}
    }},
    sysroot_repo = "{sysroot_repo}",
    sysroot_path = "{sysroot_path}",
)
"""

PLATFORMS_BUILD_ENTRY_TEMPLATE = """\
toolchain(
    name = "{name}_platform_cc",
    target_compatible_with = [
        "@platforms//cpu:{cpu}",
        "@platforms//os:{os}",
    ],
    toolchain = "@{toolchain_repo}//:{name}_cc_toolchain",
    toolchain_type = "@bazel_tools//tools/cpp:toolchain_type",
)
"""

PLATFORMS_BUILD_TEMPLATE = """\
platform(
    name = "{name}_platform",
    constraint_values = [
        "@platforms//cpu:{cpu}",
        "@platforms//os:{os}",
    ],
)
"""


@dataclass
class WrapUsage:
    wrap: HermeticPlatformWrap
    toolchain_for: T.List[HermeticPlatformInfo]
    sdk_for: T.List[HermeticPlatformInfo]


def _emit_python_requirements(output_dir: Path,
                              state_tracker: ConvertStateTracker) -> bool:  # fmt: skip
    python_libraries = state_tracker.project_config.dependencies.python_libraries
    if not python_libraries:
        return False

    bazel_dir = output_dir / 'bazel'
    bazel_dir.mkdir(parents=True, exist_ok=True)

    content = ''
    for dep, version in sorted(python_libraries.items()):
        content += f'{dep}=={version}\n'

    with open(bazel_dir / 'requirements.txt', 'w', encoding='utf-8') as f:
        f.write(content)

    # Ensure bazel/ is a package
    with open(bazel_dir / 'BUILD.bazel', 'w', encoding='utf-8') as f:
        f.write('')

    return True


def _emit_platforms(output_dir: Path, state_tracker: ConvertStateTracker,
                    copyright_string: str) -> T.Tuple[T.List[str], T.List[str], T.List[str]]:  # fmt: skip
    # This is data gleaned from the emitting platforms that will be emitted via MODULE.bazel.
    extension_usage: T.List[str] = []
    register_platforms: T.List[str] = []
    repos: T.Set[str] = set()

    unique_platforms: T.Set[HermeticPlatformInfo] = set()
    for platform_instance in state_tracker.all_platforms:
        for choice in (MachineChoice.BUILD, MachineChoice.HOST):
            platform_info = platform_instance.platforms.get(choice)
            unique_platforms.add(platform_info)

    wrap_map: T.Dict[HermeticPlatformWrap, WrapUsage] = {}
    for platform_info in unique_platforms:
        compilers_wrap = platform_info.compilers_wrap
        if compilers_wrap:
            if compilers_wrap not in wrap_map:
                wrap_map[compilers_wrap] = WrapUsage(compilers_wrap, [], [])
            wrap_map[compilers_wrap].toolchain_for.append(platform_info)

        sysroot_wrap = platform_info.sysroot_wrap
        if sysroot_wrap:
            if sysroot_wrap not in wrap_map:
                wrap_map[sysroot_wrap] = WrapUsage(sysroot_wrap, [], [])
            wrap_map[sysroot_wrap].sdk_for.append(platform_info)

    # Nothing to return: no unique platforms
    if not unique_platforms or not wrap_map:
        return ([], [], [])

    platforms_build_content = copyright_string + '\n'
    platforms_build_content += 'package(default_visibility = ["//visibility:public"])\n\n'
    platforms_build_content += 'filegroup(name = "empty")\n\n'

    platforms_dir = output_dir / 'bazel' / 'platforms'
    platforms_dir.mkdir(parents=True, exist_ok=True)

    for wrap, usage in wrap_map.items():
        wrap_name = wrap.name
        repos.add(f'"{wrap_name}"')

        if usage.toolchain_for:
            extension_usage.append(
                EXTENSION_PLATFORM_TAG_TEMPLATE.format(
                    name=wrap_name,
                    url=wrap.url,
                    sha256=wrap.sha256 or '',
                    build_file=f'//bazel/platforms:{wrap_name}_compiler.BUILD',
                    file_type='zip',
                )
            )

            # Tool paths: constant through a wrap and we just need the first
            # one
            tool_paths_items = []
            for lang_info in usage.toolchain_for[0].compiler_paths.values():
                toolchain = lang_info.toolchain_info
                if toolchain.get('wrap_name') != wrap_name:
                    continue

                for key, val in toolchain.items():
                    # Skip the keys we don't want to include
                    if key in {'wrap_name', 'name'}:
                        continue

                    # Rename 'cc' to 'gcc', otherwise use the normal key
                    if key == 'cc':
                        tool_paths_items.append(f'"gcc": "{val}"')
                    else:
                        tool_paths_items.append(f'"{key}": "{val}"')
                break

            sysroot_file_strings: T.Set[str] = set()
            for platform_info in usage.toolchain_for:
                defs_content = ''
                tool_paths_str = ',\n        '.join(tool_paths_items)
                cpu: str = platform_info.platform.get('machine_info', {}).get('cpu_family', '')
                os_name: str = platform_info.platform.get('machine_info', {}).get('system', '')

                sysroot_file_strings.add(f'"@{platform_info.sysroot_wrap.name}//:all_files"')
                sysroot_repo = f'@{platform_info.sysroot_wrap.name}'
                sysroot_path = platform_info.sysroot_path

                target_triple = f'{cpu}-{os_name}'

                defs_content += PLATFORM_DEFINITION_TEMPLATE.format(
                    name=platform_info.name,
                    cpu=cpu,
                    target_system_name=target_triple,
                    tool_paths=tool_paths_str,
                    sysroot_repo=sysroot_repo,
                    sysroot_path=sysroot_path,
                )

                register_platforms.append(
                    f'register_toolchains("//bazel/platforms:{platform_info.name}_platform_cc")'
                )

                # We add to the platforms_build_content file, which adds to the
                # bazel/platforms/BUILD.bazel
                platforms_build_content += PLATFORMS_BUILD_ENTRY_TEMPLATE.format(
                    name=platform_info.name, cpu=cpu, os=os_name, toolchain_repo=wrap_name
                )
                platforms_build_content += PLATFORMS_BUILD_TEMPLATE.format(
                    name=platform_info.name, cpu=cpu, os=os_name
                )

            if sysroot_file_strings:
                sysroot_files_str = f'[{", ".join(list(sysroot_file_strings))}]'
            else:
                sysroot_files_str = '[]'

            # Each toolchain wrap gets it's own file
            with open(platforms_dir / f'{wrap_name}_compiler.BUILD', 'w', encoding='utf-8') as f:
                f.write(
                    COMPILER_MAPPING_TEMPLATE.format(
                        sysroot_files=sysroot_files_str, definitions=defs_content
                    )
                )
        elif usage.sdk_for:
            extension_usage.append(
                EXTENSION_SYSROOT_TAG_TEMPLATE.format(
                    name=wrap_name, url=wrap.url, sha256=wrap.sha256 or ''
                )
            )

    with open(platforms_dir / 'BUILD.bazel', 'w', encoding='utf-8') as f:
        f.write(platforms_build_content)

    return (extension_usage, register_platforms, list(repos))


def _emit_bazel_rules(output_dir: Path) -> None:
    bazel_dir = output_dir / 'bazel'
    bazel_dir.mkdir(parents=True, exist_ok=True)

    # Ensure bazel/ BUILD.bazel exists
    build_file = bazel_dir / 'BUILD.bazel'
    if not build_file.exists():
        with open(build_file, 'w', encoding='utf-8') as f:
            f.write('')

    dest = bazel_dir / 'meson_rules.bzl'
    DataFile('convert/build_systems/bazel/starlark/meson_rules.bzl').write_once(dest)


def _emit_platform_extension(output_dir: Path) -> None:
    bazel_dir = output_dir / 'bazel'
    bazel_dir.mkdir(parents=True, exist_ok=True)
    dest = bazel_dir / 'platforms.bzl'
    if dest.exists():
        dest.unlink()
    DataFile('convert/build_systems/bazel/starlark/platforms.bzl').write_once(dest)


def emit_module_bazel(output_dir: Path, state_tracker: ConvertStateTracker,
                      copyright_string: str) -> None:  # fmt: skip
    (extension_usage, register_platforms, repos) = _emit_platforms(
        output_dir, state_tracker, copyright_string
    )
    _emit_bazel_rules(output_dir)
    _emit_platform_extension(output_dir)

    python_setup = ''
    if _emit_python_requirements(output_dir, state_tracker):
        python_setup = PYTHON_MODULE_SETUP_TEMPLATE

    use_repos = '\n'.join([f'use_repo(meson_repos, {r})' for r in repos])

    module_content = copyright_string + '\n'
    module_content += BAZEL_MODULE_TEMPLATE.format(
        project_name=state_tracker.project_config.project_name or 'meson_project',
        extension_usage='\n'.join(extension_usage),
        use_repos=use_repos,
        register_platforms='\n'.join(register_platforms),
        python_setup=python_setup,
    )

    with open(output_dir / 'MODULE.bazel', 'w', encoding='utf-8') as f:
        f.write(module_content)
