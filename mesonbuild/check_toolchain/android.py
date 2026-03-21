# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Authors

from __future__ import annotations
import os
import re
import sys
import tempfile
import typing as T
import copy
import hashlib
import urllib.request
import subprocess
from dataclasses import dataclass

from .defs import HostMachine, CompilerInfo, Toolchain, WrapInfo


@dataclass
class CrossFileContext:
    android_ndk_path: str
    target: str
    android_api_level: int
    rust_target: str
    system: str
    cpu_family: str
    cpu: str
    endian: str
    c_flags: T.List[str]
    cpp_flags: T.List[str]


ANDROID_CROSS_FILE_TEMPLATE = """
[binaries]
ar = '{android_ndk_path}/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-ar'
c = ['ccache', '{android_ndk_path}/toolchains/llvm/prebuilt/linux-x86_64/bin/{target}{android_api_level}-clang']
cpp = ['ccache', '{android_ndk_path}/toolchains/llvm/prebuilt/linux-x86_64/bin/{target}{android_api_level}-clang++']
rust = ['rustc', '--target', '{rust_target}']
c_ld = 'lld'
cpp_ld = 'lld'
strip = '{android_ndk_path}/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip'
pkg-config = ['/usr/bin/pkgconf']

[host_machine]
system = '{system}'
cpu_family = '{cpu_family}'
cpu = '{cpu}'
endian = '{endian}'

[built-in options]
c_args = [{c_flags_str}]
cpp_args = [{cpp_flags_str}]

[properties]
needs_exe_wrapper = true
sys_root = '{android_ndk_path}/toolchains/llvm/prebuilt/linux-x86_64/sysroot'
pkg_config_libdir = '{android_ndk_path}/toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/lib/{target}/pkgconfig/'
"""

AOSP_LINUX_COMMON_TOOLCHAIN_INFO: T.Dict[str, T.Any] = {
    "host_machine": {
        "system": "linux",
        "endian": "little",
    },
    "c": {
        "compiler_id": "clang",
        "linker_id": "ld.lld",
        "version": "21.0.0",
    },
    "cpp": {
        "compiler_id": "clang",
        "linker_id": "ld.lld",
        "version": "21.0.0",
    },
    "rust": {
        "compiler_id": "rustc",
        "linker_id": "ld.lld",
        "version": "1.90.0",
    },
    "c_headers_fails": ["pthread_np.h", "linux/udmabuf.h"],
    "c_header_symbols_fails": {
        "sys/mkdev.h": ["major", "minor", "makedev"],
        "errno.h": ["program_invocation_name"],
    },
    "c_functions_fails": [
        "memfd_create",
        "qsort_s",
        "pthread_setaffinity_np",
        "thrd_create",
        "getrandom",
        "__builtin_add_overflow_p",
        "__builtin_sub_overflow_p",
    ],
    "c_supported_arguments_fails": ["-Wno-nonnull-compare"],
    "cpp_supported_arguments_fails": ["-flifetime-dse=1"],
}


def generate_cross_file(context: CrossFileContext) -> str:
    c_flags_str = ", ".join([f"'{f}'" for f in context.c_flags])
    cpp_flags_str = ", ".join([f"'{f}'" for f in context.cpp_flags])

    return ANDROID_CROSS_FILE_TEMPLATE.format(
        android_ndk_path=context.android_ndk_path,
        target=context.target,
        android_api_level=context.android_api_level,
        rust_target=context.rust_target,
        system=context.system,
        cpu_family=context.cpu_family,
        cpu=context.cpu,
        endian=context.endian,
        c_flags_str=c_flags_str,
        cpp_flags_str=cpp_flags_str,
    )


def _get_aosp_linux_toolchain(arch: str, libc: str) -> Toolchain:
    info = copy.deepcopy(AOSP_LINUX_COMMON_TOOLCHAIN_INFO)

    if arch == "x86_64":
        info["host_machine"]["cpu_family"] = "x86_64"
        info["host_machine"]["cpu"] = "x86_64"
    elif arch == "aarch64":
        info["host_machine"]["cpu_family"] = "aarch64"
        info["host_machine"]["cpu"] = "aarch64"
    else:
        raise ValueError(f"Unsupported architecture: {arch}")

    if libc == "glibc":
        info["c_functions_fails"].append("reallocarray")
    elif libc == "musl":
        info["c_headers_fails"].append("xlocale.h")
    else:
        raise ValueError(f"Unsupported libc: {libc}")

    return Toolchain(
        name=f"linux_{libc}_{arch}",
        host_machine=HostMachine(**info["host_machine"]),
        c=CompilerInfo(**info["c"]),
        cpp=CompilerInfo(**info["cpp"]),
        rust=CompilerInfo(**info["rust"]),
        c_headers_fails=info["c_headers_fails"],
        c_header_symbols_fails=info["c_header_symbols_fails"],
        c_functions_fails=info["c_functions_fails"],
        c_supported_arguments_fails=info["c_supported_arguments_fails"],
        cpp_supported_arguments_fails=info["cpp_supported_arguments_fails"],
    )


def get_aosp_linux_toolchains() -> T.List[Toolchain]:
    toolchains: T.List[Toolchain] = []
    configs = [
        ("x86_64", "glibc"),
        ("x86_64", "musl"),
        ("aarch64", "musl"),
    ]
    for arch, libc in configs:
        toolchains.append(_get_aosp_linux_toolchain(arch, libc))
    return toolchains


@dataclass
class AndroidConfig:
    name: str
    target: str
    rust_target: str
    system: str
    cpu_family: str
    cpu: str
    endian: str
    c_flags: T.List[str]
    cpp_flags: T.List[str]


def generate_android_toolchains(
        run_compiler_checks_callback: T.Callable[
            [str, str, T.List[str], T.List[str]], Toolchain],
        ndk_version: str,
        ndk_platform: str = "linux") -> T.List[Toolchain]:  # fmt: skip
    """
    Generates and checks a set of standard Android toolchain configurations.

    This function iterates through predefined Android target configurations (e.g.,
    aarch64, x86_64, x86).

    The specified NDK version is downloaded for Bionic targets.  For build machine
    toolchains, the correct values for linux_musl and linux_glibc_* from AOSP are
    hard-coded (those toolchains are not easily downloadable).
    """
    ndk_url = f"https://dl.google.com/android/repository/android-ndk-{ndk_version}-{ndk_platform}.zip"

    temp_dir = tempfile.mkdtemp()
    ndk_zip = os.path.join(temp_dir, f"android-ndk-{ndk_version}.zip")
    print(f"Downloading Android NDK {ndk_version}: {ndk_url}...")
    urllib.request.urlretrieve(ndk_url, ndk_zip)

    sha256 = hashlib.sha256()
    with open(ndk_zip, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    ndk_hash = sha256.hexdigest()

    print(f"Extracting Android NDK {ndk_version}...")
    subprocess.run(["unzip", "-q", "-o", ndk_zip, "-d", temp_dir], check=True)

    # NDK usually extracts to a directory named android-ndk-<version>
    # But sometimes it's different, let's find it.
    extracted_dirs = [
        d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))
    ]
    if not extracted_dirs:
        sys.exit(f"Failed to find extracted NDK directory in {temp_dir}")

    # Prefer directory starting with android-ndk
    ndk_dir_name = extracted_dirs[0]
    for d in extracted_dirs:
        if d.startswith("android-ndk"):
            ndk_dir_name = d
            break

    ndk_path = os.path.join(temp_dir, ndk_dir_name)

    wrap_binaries = {
        "cc": "toolchains/llvm/prebuilt/linux-x86_64/bin/clang",
        "cpp": "toolchains/llvm/prebuilt/linux-x86_64/bin/clang++",
        "ar": "toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-ar",
        "strip": "toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip",
        "toolchain_id": "clang-android",
    }

    toolchains: T.List[Toolchain] = []
    configurations = [
        AndroidConfig(
            name="android_arm64",
            target="aarch64-linux-android",
            rust_target="aarch64-linux-android",
            system="android",
            cpu_family="aarch64",
            cpu="aarch64",
            endian="little",
            c_flags=[
                "-fno-exceptions",
                "-fno-unwind-tables",
                "-fno-asynchronous-unwind-tables",
            ],
            cpp_flags=[
                "-fno-exceptions",
                "-fno-unwind-tables",
                "-fno-asynchronous-unwind-tables",
                "--start-no-unused-arguments",
                "-static-libstdc++",
                "--end-no-unused-arguments",
            ],
        ),
        AndroidConfig(
            name="android_x86",
            target="i686-linux-android",
            rust_target="i686-linux-android",
            system="android",
            cpu_family="x86",
            cpu="i686",
            endian="little",
            c_flags=[
                "-m32",
                "-march=slm",
                "-fno-exceptions",
                "-fno-unwind-tables",
                "-fno-asynchronous-unwind-tables",
            ],
            cpp_flags=[
                "-m32",
                "-march=slm",
                "-fno-exceptions",
                "-fno-unwind-tables",
                "-fno-asynchronous-unwind-tables",
                "--start-no-unused-arguments",
                "-static-libstdc++",
                "--end-no-unused-arguments",
            ],
        ),
        AndroidConfig(
            name="android_x86_64",
            target="x86_64-linux-android",
            rust_target="x86_64-linux-android",
            system="android",
            cpu_family="x86_64",
            cpu="x86_64",
            endian="little",
            c_flags=[
                "-fno-exceptions",
                "-fno-unwind-tables",
                "-fno-asynchronous-unwind-tables",
            ],
            cpp_flags=[
                "-fno-exceptions",
                "-fno-unwind-tables",
                "-fno-asynchronous-unwind-tables",
                "--start-no-unused-arguments",
                "-static-libstdc++",
                "--end-no-unused-arguments",
            ],
        ),
    ]

    bin_path = os.path.join(
        ndk_path, "toolchains", "llvm", "prebuilt", "linux-x86_64", "bin"
    )
    api_levels = []
    for filename in os.listdir(bin_path):
        match = re.search(r"(\d+)-clang", filename)
        if match:
            api_levels.append(int(match.group(1)))

    if not api_levels:
        sys.exit(
            f"Could not determine the highest API level from the NDK path: {bin_path}"
        )

    highest_api_level = max(api_levels)
    print(f"Detected highest API level: {highest_api_level}")

    for config in configurations:
        config.c_flags.extend(
            [f"-D__ANDROID_MIN_SDK_VERSION__={highest_api_level}", "-D__USE_GNU"]
        )
        config.cpp_flags.extend(
            [f"-D__ANDROID_MIN_SDK_VERSION__={highest_api_level}", "-D__USE_GNU"]
        )

        context = CrossFileContext(
            android_ndk_path=ndk_path,
            target=config.target,
            android_api_level=highest_api_level,
            rust_target=config.rust_target,
            system=config.system,
            cpu_family=config.cpu_family,
            cpu=config.cpu,
            endian=config.endian,
            c_flags=config.c_flags,
            cpp_flags=config.cpp_flags,
        )
        cross_content = generate_cross_file(context)

        temp_cross_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".txt"
            ) as tf:
                tf.write(cross_content)
                temp_cross_file = tf.name

            t = run_compiler_checks_callback(
                temp_cross_file,
                config.name,
                config.c_flags,
                config.cpp_flags,
            )

            t.compilers_wrap = WrapInfo(
                source_url=ndk_url,
                source_filename=os.path.basename(ndk_url),
                source_hash=ndk_hash,
                binaries=wrap_binaries,
            )

            toolchains.append(t)
        finally:
            if temp_cross_file:
                os.unlink(temp_cross_file)

    toolchains += get_aosp_linux_toolchains()
    return toolchains
