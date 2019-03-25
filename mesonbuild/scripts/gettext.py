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

import os
import shutil
import argparse
import subprocess
from . import destdir_join

parser = argparse.ArgumentParser()
parser.add_argument('command')
parser.add_argument('--pkgname', default='')
parser.add_argument('--datadirs', default='')
parser.add_argument('--langs', default='')
parser.add_argument('--localedir', default='')
parser.add_argument('--subdir', default='')
parser.add_argument('--extra-args', default='')

def read_linguas(src_sub):
    # Syntax of this file is documented here:
    # https://www.gnu.org/software/gettext/manual/html_node/po_002fLINGUAS.html
    linguas = os.path.join(src_sub, 'LINGUAS')
    try:
        langs = []
        with open(linguas) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    langs += line.split()
        return langs
    except (FileNotFoundError, PermissionError):
        print('Could not find file LINGUAS in {}'.format(src_sub))
        return []

def run_potgen(src_sub, pkgname, datadirs, args):
    listfile = os.path.join(src_sub, 'POTFILES.in')
    if not os.path.exists(listfile):
        listfile = os.path.join(src_sub, 'POTFILES')
        if not os.path.exists(listfile):
            print('Could not find file POTFILES in %s' % src_sub)
            return 1

    child_env = os.environ.copy()
    if datadirs:
        child_env['GETTEXTDATADIRS'] = datadirs

    ofile = os.path.join(src_sub, pkgname + '.pot')
    return subprocess.call(['xgettext', '--package-name=' + pkgname, '-p', src_sub, '-f', listfile,
                            '-D', os.environ['MESON_SOURCE_ROOT'], '-k_', '-o', ofile] + args,
                           env=child_env)

def gen_gmo(src_sub, bld_sub, langs):
    for l in langs:
        subprocess.check_call(['msgfmt', os.path.join(src_sub, l + '.po'),
                               '-o', os.path.join(bld_sub, l + '.gmo')])
    return 0

def update_po(src_sub, pkgname, langs):
    potfile = os.path.join(src_sub, pkgname + '.pot')
    for l in langs:
        pofile = os.path.join(src_sub, l + '.po')
        if os.path.exists(pofile):
            subprocess.check_call(['msgmerge', '-q', '-o', pofile, pofile, potfile])
        else:
            subprocess.check_call(['msginit', '--input', potfile, '--output-file', pofile, '--locale', l, '--no-translator'])
    return 0

def do_install(src_sub, bld_sub, dest, pkgname, langs):
    for l in langs:
        srcfile = os.path.join(bld_sub, l + '.gmo')
        outfile = os.path.join(dest, l, 'LC_MESSAGES',
                               pkgname + '.mo')
        tempfile = outfile + '.tmp'
        os.makedirs(os.path.dirname(outfile), exist_ok=True)
        shutil.copyfile(srcfile, tempfile)
        shutil.copystat(srcfile, tempfile)
        os.replace(tempfile, outfile)
        print('Installing %s to %s' % (srcfile, outfile))
    return 0

def run(args):
    options = parser.parse_args(args)
    subcmd = options.command
    langs = options.langs.split('@@') if options.langs else None
    extra_args = options.extra_args.split('@@') if options.extra_args else []
    subdir = os.environ.get('MESON_SUBDIR', '')
    if options.subdir:
        subdir = options.subdir
    src_sub = os.path.join(os.environ['MESON_SOURCE_ROOT'], subdir)
    bld_sub = os.path.join(os.environ['MESON_BUILD_ROOT'], subdir)

    if not langs:
        langs = read_linguas(src_sub)

    if subcmd == 'pot':
        return run_potgen(src_sub, options.pkgname, options.datadirs, extra_args)
    elif subcmd == 'gen_gmo':
        return gen_gmo(src_sub, bld_sub, langs)
    elif subcmd == 'update_po':
        if run_potgen(src_sub, options.pkgname, options.datadirs, extra_args) != 0:
            return 1
        return update_po(src_sub, options.pkgname, langs)
    elif subcmd == 'install':
        destdir = os.environ.get('DESTDIR', '')
        dest = destdir_join(destdir, os.path.join(os.environ['MESON_INSTALL_PREFIX'],
                                                  options.localedir))
        if gen_gmo(src_sub, bld_sub, langs) != 0:
            return 1
        do_install(src_sub, bld_sub, dest, options.pkgname, langs)
    else:
        print('Unknown subcommand.')
        return 1
