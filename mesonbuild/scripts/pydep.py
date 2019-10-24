# Copyright 2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
import atexit
import argparse

from importlib import invalidate_caches
from importlib.machinery import FileFinder, SourceFileLoader

def escape(val):
    return val.replace(' ', '\\ ').replace('$', '$$').replace('#', '\\#')


class DepLoader(SourceFileLoader):
    loaded = set()

    def get_code(self, fullname):
        loaded = escape(self.get_filename(fullname))
        self.loaded.add(loaded)
        return super().get_code(fullname)


def exit_handler(opts):
    if not opts.output:
        opts.output = opts.script
    if not opts.depfile:
        opts.depfile = os.path.basename(opts.script) + '.d'

    output = escape(opts.output)
    with open(opts.depfile, 'w') as out:
        print('%s: %s' % (output, ' '.join(DepLoader.loaded)), file=out)


def run(args):
    parser = argparse.ArgumentParser(
        description='Generate depfile for python scripts')

    parser.add_argument('-o', '--output',
                        help='Output filename')
    parser.add_argument('-d', '--depfile',
                        help='depfile filename location')
    parser.add_argument('script', nargs='?',
                        help='Python program to run')
    parser.add_argument('arguments', nargs=argparse.REMAINDER,
                        help='script arguments')

    opts = parser.parse_args(args)

    if opts.script is None:
        parser.error('script is missing')

    sys.argv = [opts.script, *opts.arguments]
    sys.path[0] = os.path.dirname(opts.script)

    # credits to:
    # https://stackoverflow.com/a/43573798/1277510
    loader_details = DepLoader, [".py"]
    # insert the path hook ahead of other path hooks
    sys.path_hooks.insert(0, FileFinder.path_hook(loader_details))
    # clear any loaders that might already be in use by the FileFinder
    sys.path_importer_cache.clear()
    invalidate_caches()

    atexit.register(exit_handler, opts)

    try:
        # credits to cpython trace.py
        with open(opts.script) as fp:
            code = compile(fp.read(), opts.script, 'exec')
        # try to emulate __main__ namespace as much as possible
        globs = {
            '__file__': opts.script,
            '__name__': '__main__',
            '__package__': None,
            '__cached__': None,
        }
        exec(code, globs, globs)
    except OSError as err:
        sys.exit("Cannot run file %r because: %s" % (sys.argv[0], err))
    except SystemExit as e:
        return e.code
    return 1


if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
