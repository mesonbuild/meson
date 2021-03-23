#!/usr/bin/env python3
# SPDX-license-identifier: Apache-2.0
# Copyright © 2021 Intel Corporation

"""Script for running a single project test.

This script is meant for Meson developers who want to run a single project
test, with all of the rules from the test.json file loaded.
"""

import argparse
import pathlib
import shutil
import typing as T

from mesonbuild import environment
from mesonbuild import mlog
from mesonbuild import mesonlib
from run_project_tests import TestDef, load_test_json, run_test, BuildStep, skippable
from run_tests import get_backend_commands, guess_backend, get_fake_options

if T.TYPE_CHECKING:
    try:
        from typing import Protocol
    except ImportError:
        # Mypy gets grump about this even though it's fine
        from typing_extensions import Protocol  # type: ignore

    class ArgumentType(Protocol):

        """Typing information for command line arguments."""

        case: pathlib.Path
        subtests: T.List[int]
        backend: str


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('case', type=pathlib.Path, help='The test case to run')
    parser.add_argument('--subtest', type=int, action='append', dest='subtests', help='which subtests to run')
    parser.add_argument('--backend', action='store', help="Which backend to use")
    args = T.cast('ArgumentType', parser.parse_args())

    test = TestDef(args.case, args.case.stem, [])
    tests = load_test_json(test, False)
    if args.subtests:
        tests = [t for i, t in enumerate(tests) if i in args.subtests]

    with mesonlib.TemporaryDirectoryWinProof() as build_dir:
        fake_opts = get_fake_options('/')
        env = environment.Environment(None, build_dir, fake_opts)
        try:
            comp = env.compiler_from_language('c', mesonlib.MachineChoice.HOST).get_id()
        except mesonlib.MesonException:
            raise RuntimeError('Could not detect C compiler')

    backend, backend_args = guess_backend(args.backend, shutil.which('msbuild'))
    _cmds = get_backend_commands(backend, False)
    commands = (_cmds[0], _cmds[1], _cmds[3], _cmds[4])

    results = [run_test(t, t.args, comp, backend, backend_args, commands, False, True) for t in tests]
    failed = False
    for test, result in zip(tests, results):
        if (result is None) or (('MESON_SKIP_TEST' in result.stdo) and (skippable(str(args.case.parent), test.path.as_posix()))):
            msg = mlog.yellow('SKIP:')
        elif result.msg:
            msg = mlog.red('FAIL:')
            failed = True
        else:
            msg = mlog.green('PASS:')
        mlog.log(msg, test.display_name())
        if result.msg and 'MESON_SKIP_TEST' not in result.stdo:
            mlog.log('reason:', result.msg)
            if result.step is BuildStep.configure:
                # For configure failures, instead of printing stdout,
                # print the meson log if available since it's a superset
                # of stdout and often has very useful information.
                mlog.log(result.mlog)
            else:
                mlog.log(result.stdo)
            for cmd_res in result.cicmds:
                mlog.log(cmd_res)
            mlog.log(result.stde)

    exit(1 if failed else 0)

if __name__ == "__main__":
    main()
