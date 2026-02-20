# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson development team

import subprocess
import tempfile
from pathlib import Path

from .baseplatformtests import BasePlatformTests
from mesonbuild.cargo.toml import load_toml


class CheckToolchainTests(BasePlatformTests):
    def test_native_check_toolchain(self) -> None:
        with tempfile.TemporaryDirectory() as output_dir:
            output_file = Path(output_dir) / "output.toml"
            command = self.meson_command + [
                "check-toolchain",
                "--output",
                str(output_file),
                "--name",
                "test-native",
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
            self.assertTrue(output_file.exists(), "Output TOML file was not generated")

            data = load_toml(str(output_file))
            self.assertIn("toolchain", data)
            toolchains = data["toolchain"]
            self.assertIsInstance(toolchains, list)
            self.assertGreater(len(toolchains), 0)

            native = toolchains[0]
            self.assertEqual(native["name"], "test-native")
            self.assertIn("host_machine", native)
            host = native["host_machine"]
            self.assertIn("cpu_family", host)
            self.assertIn("system", host)
            self.assertIn("cpu", host)
            self.assertIn("endian", host)

            self.assertIn("c", native)
            self.assertIn("compiler_id", native["c"])
            self.assertIn("version", native["c"])

            self.assertIn("cpp", native)
            self.assertIn("compiler_id", native["cpp"])
            self.assertIn("version", native["cpp"])
