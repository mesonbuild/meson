# SPDX-license-identifier: Apache-2.0
# Copyright © 2021 Intel Corporation

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Portable script for doing sed-like regex replacements."""

import argparse
import re
import sys
import typing as T

if T.TYPE_CHECKING:
    from typing_extensions import Protocol

    class Arguments(Protocol):
        input: str
        ouput: str
        regexes: T.List[T.Tuple[str, str]]


def run(raw: T.List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='The template file')
    parser.add_argument('ouput', help='Where to write the output')
    parser.add_argument('--regex', dest='regexes', nargs=2, action='append', default=[])
    args: 'Arguments' = parser.parse_args(raw)

    with open(args.input, 'r', encoding='utf-8') as f:
        content = f.read()

    for holder, replacment in args.regexes:
        content = re.sub(holder, replacment, content)

    with open(args.ouput, 'w', encoding='utf-8') as f:
        f.write(content)

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv))
