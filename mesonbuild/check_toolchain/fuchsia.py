# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Authors

from __future__ import annotations
import os
import hashlib
import tempfile
import urllib.request
import subprocess
import typing as T
from dataclasses import dataclass

from .defs import Toolchain, WrapInfo


@dataclass
class FuchsiaConfig:
    name: str
    target: str
    cpu_family: str
    cpu: str
    endian: str
    sysroot_arch: str


FUCHSIA_CROSS_FILE_TEMPLATE = """
[binaries]
c = ['{cc_path}', '--target={target}', '--sysroot={sysroot}']
cpp = ['{cpp_path}', '--target={target}', '--sysroot={sysroot}']
ar = '{ar_path}'
strip = '{strip_path}'
c_ld = 'lld'
cpp_ld = 'lld'

[host_machine]
system = 'fuchsia'
cpu_family = '{cpu_family}'
cpu = '{cpu}'
endian = '{endian}'
"""


def generate_fuchsia_toolchains(
        clang_instance_id: str,
        sdk_instance_id: str,
        run_compiler_checks_callback: T.Callable[
            [str, str, T.List[str], T.List[str]], Toolchain]) -> T.List[Toolchain]:  # fmt: skip
    """
    Downloads a Fuchsia Clang toolchain and Core SDK to perform compiler checks.

    This function fetches both the toolchain and the SDK from Chrome Infrastructure Package
    Deployment (CIPD).

    It identifies the sysroot paths within the SDK for each target architecture
    and uses them to generate accurate compiler checks.
    """
    clang_url = f"https://chrome-infra-packages.appspot.com/dl/fuchsia/third_party/clang/linux-amd64/+/{clang_instance_id}"
    sdk_url = f"https://chrome-infra-packages.appspot.com/dl/fuchsia/sdk/core/linux-amd64/+/{sdk_instance_id}"

    with tempfile.TemporaryDirectory() as temp_dir:
        # Download and extract Clang
        clang_zip = os.path.join(temp_dir, "fuchsia-clang.zip")
        print(f"Downloading Clang: {clang_url}...")
        urllib.request.urlretrieve(clang_url, clang_zip)

        sha256 = hashlib.sha256()
        with open(clang_zip, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        clang_hash = sha256.hexdigest()

        clang_extract_path = os.path.join(temp_dir, "clang_extract")
        os.makedirs(clang_extract_path, exist_ok=True)
        subprocess.run(
            ["unzip", "-q", "-o", clang_zip, "-d", clang_extract_path], check=True
        )

        # Download and extract SDK
        sdk_zip = os.path.join(temp_dir, "fuchsia-sdk.zip")
        print(f"Downloading SDK: {sdk_url}...")
        urllib.request.urlretrieve(sdk_url, sdk_zip)

        sha256 = hashlib.sha256()
        with open(sdk_zip, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        sdk_hash = sha256.hexdigest()

        sdk_extract_path = os.path.join(temp_dir, "sdk_extract")
        os.makedirs(sdk_extract_path, exist_ok=True)
        subprocess.run(
            ["unzip", "-q", "-o", sdk_zip, "-d", sdk_extract_path], check=True
        )

        wrap_binaries = {
            "cc": "bin/clang",
            "cpp": "bin/clang++",
            "ld": "bin/ld.lld",
            "ar": "bin/llvm-ar",
            "nm": "bin/llvm-nm",
            "objcopy": "bin/llvm-objcopy",
            "objdump": "bin/llvm-objdump",
            "gcov": "bin/llvm-cov",
            "strip": "bin/llvm-strip",
            "as": "bin/llvm-as",
            "toolchain_id": "clang-fuchsia",
        }

        configurations = [
            FuchsiaConfig(
                name="fuchsia_x86_64",
                target="x86_64-unknown-fuchsia",
                cpu_family="x86_64",
                cpu="x86_64",
                endian="little",
                sysroot_arch="x64",
            ),
            FuchsiaConfig(
                name="fuchsia_aarch64",
                target="aarch64-unknown-fuchsia",
                cpu_family="aarch64",
                cpu="aarch64",
                endian="little",
                sysroot_arch="arm64",
            ),
            FuchsiaConfig(
                name="fuchsia_riscv",
                target="riscv64-unknown-fuchsia",
                cpu_family="riscv64",
                cpu="riscv64",
                endian="little",
                sysroot_arch="riscv64",
            ),
        ]

        toolchains = []
        for config in configurations:
            cc_path = os.path.join(clang_extract_path, "bin", "clang")
            cpp_path = os.path.join(clang_extract_path, "bin", "clang++")
            ar_path = os.path.join(clang_extract_path, "bin", "llvm-ar")
            strip_path = os.path.join(clang_extract_path, "bin", "llvm-strip")
            sysroot_path = os.path.join(
                sdk_extract_path, "arch", config.sysroot_arch, "sysroot"
            )

            if not os.path.exists(sysroot_path):
                print(f"Warning: sysroot not found for {config.name} at {sysroot_path}")

            cross_content = FUCHSIA_CROSS_FILE_TEMPLATE.format(
                cc_path=cc_path,
                cpp_path=cpp_path,
                ar_path=ar_path,
                strip_path=strip_path,
                target=config.target,
                sysroot=sysroot_path,
                cpu_family=config.cpu_family,
                cpu=config.cpu,
                endian=config.endian,
            )

            temp_cross_file = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", delete=False, suffix=".txt"
                ) as tf:
                    tf.write(cross_content)
                    temp_cross_file = tf.name

                t = run_compiler_checks_callback(temp_cross_file, config.name, [], [])

                # The Fuchsia SDK does have memfd_create, but not MFD_CLOEXEC | MFD_ALLOW_SEALING.
                # Those are so common we might as well report not having memfd.
                if "memfd_create" not in t.c_functions_fails:
                    t.c_functions_fails.append("memfd_create")

                t.compilers_wrap = WrapInfo(
                    source_url=clang_url,
                    source_filename="fuchsia-clang-linux-amd64.zip",
                    source_hash=clang_hash,
                    binaries=wrap_binaries,
                )
                t.sysroot_wrap = WrapInfo(
                    source_url=sdk_url,
                    source_filename="fuchsia-sdk-core-linux-amd64.zip",
                    source_hash=sdk_hash,
                    binaries={},
                )
                toolchains.append(t)
            finally:
                if temp_cross_file:
                    os.unlink(temp_cross_file)

        return toolchains
