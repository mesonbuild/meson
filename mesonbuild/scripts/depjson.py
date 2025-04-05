# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 The Meson development team

import argparse
import json
import typing as T

def run(args: T.List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('depname')
    parser.add_argument('output')
    parser.add_argument('introdeps_fname')
    options = parser.parse_args(args)

    with open(options.introdeps_fname, encoding='utf-8') as fp:
        data = json.load(fp)

    for item in data:
        if item['name'] == options.depname:
            with open(options.output, 'w', encoding='utf-8') as fp:
                json.dump(item, fp)
            break
    else:
        parser.error(f'internal error: {options.depname} not found')

    return 0
