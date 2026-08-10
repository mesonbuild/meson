#!/usr/bin/env python3
"""
Standalone regression check for mesonbuild/msubprojects.py's run().

Simulates the Windows cross-mount/UNC scenario where os.path.relpath()
raises ValueError ("path is on mount X, start on mount Y") by monkeypatching
os.path.relpath to always raise, then invoking msubprojects.run() with
minimal fake arguments.

Exit 0: run() handled the ValueError gracefully (fix present).
Exit 1: the ValueError propagated uncaught (bug still present).
"""
import os
import sys
import tempfile

import mesonbuild.msubprojects as msubprojects


class FakeArguments:
    def __init__(self, sourcedir):
        self.sourcedir = sourcedir
        # Attributes accessed later in run(); a bare 'subprojects.func' is
        # not reached because run() returns early (no meson.build found)
        # once source_dir is successfully computed, which is all we need
        # to exercise the fixed code path around line ~723.
        self.subprojects_func = None


def main() -> int:
    real_relpath = os.path.relpath

    def raising_relpath(*args, **kwargs):
        raise ValueError("path is on mount 'Z:', start on mount 'C:'")

    os.path.relpath = raising_relpath
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            options = FakeArguments(tmpdir)
            try:
                msubprojects.run(options)
            except ValueError as e:
                print(f"FAIL: ValueError propagated uncaught: {e}")
                return 1
            except Exception as e:
                # Any other exception means we got past the relpath call
                # without crashing on ValueError -- that's what we're
                # checking for. Still report it for visibility.
                print(f"OK: relpath ValueError was handled (got {type(e).__name__}: {e})")
                return 0
            else:
                print("OK: run() returned without raising")
                return 0
    finally:
        os.path.relpath = real_relpath


if __name__ == '__main__':
    sys.exit(main())
