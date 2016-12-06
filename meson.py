#!/usr/bin/env python3

# Copyright 2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mesonbuild import mlog, mesonmain, mesonlib
import sys, os, locale

def main():
    # Warn if the locale is not UTF-8. This can cause various unfixable issues
    # such as os.stat not being able to decode filenames with unicode in them.
    # There is no way to reset both the preferred encoding and the filesystem
    # encoding, so we can just warn about it.
    e = locale.getpreferredencoding()
    if e.upper() != 'UTF-8' and not mesonlib.is_windows():
        mlog.warning('You are using {!r} which is not a a Unicode-compatible '
                     'locale.'.format(e))
        mlog.warning('You might see errors if you use UTF-8 strings as '
                     'filenames, as strings, or as file contents.')
        mlog.warning('Please switch to a UTF-8 locale for your platform.')
    # Always resolve the command path so Ninja can find it for regen, tests, etc.
    launcher = os.path.realpath(sys.argv[0])
    return mesonmain.run(launcher, sys.argv[1:])

if __name__ == '__main__':
    sys.exit(main())
