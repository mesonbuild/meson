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

import os, subprocess, shutil
from mesonbuild.scripts import destdir_join

def run_potgen(src_sub, pkgname, args):
    listfile = os.path.join(src_sub, 'POTFILES')
    if not os.path.exists(listfile):
        listfile = os.path.join(src_sub, 'POTFILES.in')
        if not os.path.exists(listfile):
            print('Could not find file POTFILES in %s' % src_sub)
            return 1

    ofile = os.path.join(src_sub, pkgname + '.pot')
    return subprocess.call(['xgettext', '--package-name=' + pkgname, '-p', src_sub, '-f', listfile,
                            '-D', os.environ['MESON_SOURCE_ROOT'], '-k_', '-o', ofile] + args)

def gen_gmo(src_sub, bld_sub, langs):
    for l in langs:
        subprocess.check_call(['msgfmt', os.path.join(src_sub, l + '.po'),
                               '-o', os.path.join(bld_sub, l + '.gmo')])
    return 0

def do_install(src_sub, bld_sub, dest, pkgname, langs):
    for l in langs:
        srcfile = os.path.join(bld_sub, l + '.gmo')
        outfile = os.path.join(dest, l, 'LC_MESSAGES',
                               pkgname + '.mo')
        os.makedirs(os.path.split(outfile)[0], exist_ok=True)
        shutil.copyfile(srcfile, outfile)
        shutil.copystat(srcfile, outfile)
        print('Installing %s to %s.' % (srcfile, outfile))
    return 0

def run(args):
    subcmd = args[0]
    if subcmd == 'pot':
        src_sub = os.path.join(os.environ['MESON_SOURCE_ROOT'], os.environ['MESON_SUBDIR'])
        bld_sub = os.path.join(os.environ['MESON_BUILD_ROOT'], os.environ['MESON_SUBDIR'])
        return run_potgen(src_sub, args[1], args[2:])
    elif subcmd == 'gen_gmo':
        src_sub = os.path.join(os.environ['MESON_SOURCE_ROOT'], os.environ['MESON_SUBDIR'])
        bld_sub = os.path.join(os.environ['MESON_BUILD_ROOT'], os.environ['MESON_SUBDIR'])
        return gen_gmo(src_sub, bld_sub, args[1:])
    elif subcmd == 'install':
        subdir = args[1]
        pkgname = args[2]
        instsubdir = args[3]
        langs = args[4:]
        src_sub = os.path.join(os.environ['MESON_SOURCE_ROOT'], subdir)
        bld_sub = os.path.join(os.environ['MESON_BUILD_ROOT'], subdir)
        destdir = os.environ.get('DESTDIR', '')
        dest = destdir_join(destdir, os.path.join(os.environ['MESON_INSTALL_PREFIX'], instsubdir))
        if gen_gmo(src_sub, bld_sub, langs) != 0:
            return 1
        do_install(src_sub, bld_sub, dest, pkgname, langs)
    else:
        print('Unknown subcommand.')
        return 1
