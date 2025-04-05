# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 The Meson development team

import argparse
import json
import typing as T

def run(args: T.List[str]) -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument('output')

    parser.add_argument('name')
    parser.add_argument('type')
    parser.add_argument('version')

    parser.add_argument('--compile_args', action='append', default=[])
    parser.add_argument('--link_args', action='append', default=[])
    parser.add_argument('--include_directories', action='append', default=[])
    parser.add_argument('--sources', action='append', default=[])
    parser.add_argument('--extra_files', action='append', default=[])

    parser.add_argument('--dependencies', action='append', default=[])
    parser.add_argument('--depends', action='append', default=[])

    options = parser.parse_args(args)

    # This must be the same format as meson introspect --dependencies
    data = {
        'name': options.name,
        'type': options.type,
        'version': options.version,
        'compile_args': options.compile_args,
        'link_args': options.link_args,
        'include_directories': options.include_directories,
        'sources': options.sources,
        'extra_files': options.extra_files,
        'dependencies': options.dependencies,
        'depends': options.depends,
    }

    with open(options.output, 'w', encoding='utf-8') as fp:
        json.dump(data, fp)

    return 0
