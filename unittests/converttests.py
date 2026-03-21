# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson development team

import os
import subprocess
import sys
import unittest
from pathlib import Path
import tempfile

from .baseplatformtests import BasePlatformTests


@unittest.skipIf(sys.version_info < (3, 11), "convert feature requires Python 3.11 or newer")
class ConvertTests(BasePlatformTests):
    def setUp(self) -> None:
        super().setUp()
        self.src_root = Path(__file__).resolve().parent.parent
        self.convert_test_dir = self.src_root / "test cases/convert"

    def _compare_directories(self, expected_dir: Path, actual_dir: Path, filename: str):
        for root, _, files in os.walk(expected_dir):
            if filename in files:
                rel_path = Path(root).relative_to(expected_dir)
                expected_file = Path(root) / filename
                actual_file = actual_dir / rel_path / filename

                self.assertTrue(
                    actual_file.exists(), f"Expected file {actual_file} does not exist"
                )

                expected_content = expected_file.read_text(encoding="utf-8").strip()
                actual_content = actual_file.read_text(encoding="utf-8").strip()

                self.assertEqual(
                    actual_content,
                    expected_content,
                    f"Content mismatch in {actual_file}",
                )

    def test_soong_conversion(self):
        with tempfile.TemporaryDirectory() as output_dir:
            test_dir = self.convert_test_dir / "1 basic"

            command = self.meson_command + [
                "convert",
                "test",
                "basic_soong",
                "--project-dir",
                str(test_dir),
                "--output-dir",
                output_dir,
            ]

            p = subprocess.run(
                command, capture_output=True, encoding="utf-8", text=True
            )
            if p.returncode != 0:
                print("STDOUT:")
                print(p.stdout)
                print("STDERR:")
                print(p.stderr)

            self.assertEqual(p.returncode, 0)
            self._compare_directories(test_dir, Path(output_dir), "Android.bp")

    def test_bazel_conversion(self):
        with tempfile.TemporaryDirectory() as output_dir:
            test_dir = self.convert_test_dir / "1 basic"

            command = self.meson_command + [
                "convert",
                "test",
                "basic_bazel",
                "--project-dir",
                str(test_dir),
                "--output-dir",
                output_dir,
            ]

            p = subprocess.run(
                command, capture_output=True, encoding="utf-8", text=True
            )
            if p.returncode != 0:
                print("STDOUT:")
                print(p.stdout)
                print("STDERR:")
                print(p.stderr)

            self.assertEqual(p.returncode, 0)
            self._compare_directories(test_dir, Path(output_dir), "BUILD.bazel")
