#!/usr/bin/env python3
# Copyright 2018 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import argparse
import os
import subprocess
import sys
import traceback


def check_pr(is_pr_env):
    if is_pr_env not in os.environ:
        print('This is not pull request: {} is not set'.format(is_pr_env))
        sys.exit()
    elif os.environ[is_pr_env] == 'false':
        print('This is not pull request: {} is false'.format(is_pr_env))
        sys.exit()


def get_base_branch(base_env):
    if base_env not in os.environ:
        print('Unable to determine base branch: {} is not set'.format(base_env))
        sys.exit()
    return os.environ[base_env]


def get_git_files(base):
    diff = subprocess.check_output(['git', 'diff', '--name-only', base + '...HEAD'])
    return diff.strip().split(b'\n')


def is_documentation(filename):
    return filename.startswith(b'docs/')


def main():
    try:
        parser = argparse.ArgumentParser(description='CI Skipper')
        parser.add_argument('--base-branch-env', required=True,
                            help='Branch push is targeted to')
        parser.add_argument('--is-pull-env', required=True,
                            help='Variable set if it is a PR')
        parser.add_argument('--base-branch-origin', action='store_true',
                            help='Base branch reference is only in origin remote')
        args = parser.parse_args()
        check_pr(args.is_pull_env)
        base = get_base_branch(args.base_branch_env)
        if args.base_branch_origin:
            base = 'origin/' + base
        if all(is_documentation(f) for f in get_git_files(base)):
            print("Don't run CI for documentation-only changes, add '[skip ci]' to commit title.")
            print('See http://mesonbuild.com/Contributing.html#skipping-integration-tests')
            sys.exit(1)
    except Exception:
        # If this script fails we want build to proceed.
        # Failure likely means some corner case we did not consider or bug.
        # Either case this should not prevent CI from running if it is needed,
        # and we tolerate it if it is run where it is not required.
        traceback.print_exc()
        print('There is a BUG in skip_ci.py, exiting.')
        sys.exit()

if __name__ == '__main__':
    main()
