# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 The Meson development team

from __future__ import annotations

import dataclasses
import shutil
import subprocess
import sys
import typing as T


@dataclasses.dataclass
class DependencyCheckResult:
    """Result of a cross-compilation dependency pre-flight check."""
    all_ok: bool = True
    missing_binaries: T.Dict[str, str] = dataclasses.field(default_factory=dict)
    missing_packages: T.Dict[str, str] = dataclasses.field(default_factory=dict)

    def add_missing_binary(self, name: str, reason: str) -> None:
        self.missing_binaries[name] = reason
        self.all_ok = False

    def add_missing_package(self, name: str, reason: str) -> None:
        self.missing_packages[name] = reason
        self.all_ok = False


class DependencyChecker:
    """Validates that cross-compilation prerequisites are installed.

    Reads ``[required_binaries]`` and ``[required_packages]`` sections from a
    parsed machine-file sections dictionary and checks that each is available.
    """

    def __init__(self, sections: T.Dict[str, T.Dict[str, T.Any]]) -> None:
        self._required_binaries: T.Dict[str, str] = {}
        self._required_packages: T.Dict[str, str] = {}

        raw_binaries = sections.get('required_binaries', {})
        for k, v in raw_binaries.items():
            self._required_binaries[str(k)] = str(v) if v is not None else ''

        raw_packages = sections.get('required_packages', {})
        for k, v in raw_packages.items():
            self._required_packages[str(k)] = str(v) if v is not None else ''

    def check(self) -> DependencyCheckResult:
        """Run all dependency checks, collecting every failure."""
        result = DependencyCheckResult()

        for binary, _version in self._required_binaries.items():
            found = shutil.which(binary)
            if found is None:
                result.add_missing_binary(binary, 'not found on PATH')

        for pkg, _version in self._required_packages.items():
            if not self._check_system_package(pkg):
                result.add_missing_package(pkg, self._pkg_install_hint(pkg))

        return result

    @staticmethod
    def _check_system_package(pkg_name: str) -> bool:
        if not sys.platform.startswith('linux'):
            return True  # can't check on non-Linux; don't block
        try:
            subprocess.run(
                ['dpkg-query', '-W', '-f', '${Status}', pkg_name],
                capture_output=True, text=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        try:
            subprocess.run(
                ['rpm', '-q', pkg_name],
                capture_output=True, text=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return False

    @staticmethod
    def _pkg_install_hint(pkg_name: str) -> str:
        if sys.platform.startswith('linux'):
            return f'Try: apt install {pkg_name}  or  dnf install {pkg_name}'
        return 'Please install this package manually'

    @staticmethod
    def format_report(result: DependencyCheckResult) -> str:
        """Build a human-readable report from a check result."""
        lines: T.List[str] = []
        if result.missing_binaries:
            lines.append('Missing binaries (not found on PATH):')
            for name, reason in sorted(result.missing_binaries.items()):
                lines.append(f'  - {name}: {reason}')
        if result.missing_packages:
            lines.append('Missing system packages:')
            for name, reason in sorted(result.missing_packages.items()):
                lines.append(f'  - {name}: {reason}')
        if not lines:
            lines.append('All cross-compilation dependencies are satisfied.')
        return '\n'.join(lines)
