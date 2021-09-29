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
import subprocess
import shutil
import argparse
from .. import mlog
from ..mesonlib import has_path_sep
from . import destdir_join
from .gettext import read_linguas
import typing as T

parser = argparse.ArgumentParser()
parser.add_argument('command')
parser.add_argument('--id', dest='project_id')
parser.add_argument('--subdir', dest='subdir')
parser.add_argument('--installdir', dest='install_dir')
parser.add_argument('--sources', dest='sources')
parser.add_argument('--media', dest='media', default='')
parser.add_argument('--langs', dest='langs', default='')
parser.add_argument('--symlinks', type=bool, dest='symlinks', default=False)

def build_pot(srcdir: str, project_id: str, sources: T.List[str]) -> None:
    # Must be relative paths
    sources = [os.path.join('C', source) for source in sources]
    outfile = os.path.join(srcdir, project_id + '.pot')
    subprocess.call(['itstool', '-o', outfile] + sources)

def update_po(srcdir: str, project_id: str, langs: T.List[str]) -> None:
    potfile = os.path.join(srcdir, project_id + '.pot')
    for lang in langs:
        pofile = os.path.join(srcdir, lang, lang + '.po')
        subprocess.call(['msgmerge', '-q', '-o', pofile, pofile, potfile])

def build_translations(srcdir: str, blddir: str, langs: T.List[str]) -> None:
    for lang in langs:
        outdir = os.path.join(blddir, lang)
        os.makedirs(outdir, exist_ok=True)
        subprocess.call([
            'msgfmt', os.path.join(srcdir, lang, lang + '.po'),
            '-o', os.path.join(outdir, lang + '.gmo')
        ])

def merge_translations(blddir: str, sources: T.List[str], langs: T.List[str]) -> None:
    for lang in langs:
        subprocess.call([
            'itstool', '-m', os.path.join(blddir, lang, lang + '.gmo'),
            '-o', os.path.join(blddir, lang)
        ] + sources)

def install_help(srcdir: str, blddir: str, sources: T.List[str], media: T.List[str], langs: T.List[str], install_dir: str, destdir: str, project_id: str, symlinks: bool) -> None:
    c_install_dir = os.path.join(install_dir, 'C', project_id)
    for lang in langs + ['C']:
        indir = destdir_join(destdir, os.path.join(install_dir, lang, project_id))
        os.makedirs(indir, exist_ok=True)
        for source in sources:
            infile = os.path.join(srcdir if lang == 'C' else blddir, lang, source)
            outfile = os.path.join(indir, source)
            mlog.log(f'Installing {infile} to {outfile}')
            shutil.copy2(infile, outfile)
        for m in media:
            infile = os.path.join(srcdir, lang, m)
            outfile = os.path.join(indir, m)
            c_infile = os.path.join(srcdir, 'C', m)
            if not os.path.exists(infile):
                if not os.path.exists(c_infile):
                    mlog.warning('Media file "%s" did not exist in C directory' % m)
                    continue
                elif symlinks:
                    srcfile = os.path.join(c_install_dir, m)
                    mlog.log(f'Symlinking {outfile} to {srcfile}.')
                    if has_path_sep(m):
                        os.makedirs(os.path.dirname(outfile), exist_ok=True)
                    try:
                        try:
                            os.symlink(srcfile, outfile)
                        except FileExistsError:
                            os.remove(outfile)
                            os.symlink(srcfile, outfile)
                        continue
                    except (NotImplementedError, OSError):
                        mlog.warning('Symlinking not supported, falling back to copying')
                        infile = c_infile
                else:
                    # Lang doesn't have media file so copy it over 'C' one
                    infile = c_infile
            mlog.log(f'Installing {infile} to {outfile}')
            if has_path_sep(m):
                os.makedirs(os.path.dirname(outfile), exist_ok=True)
            shutil.copyfile(infile, outfile)
            shutil.copystat(infile, outfile)

def run(args: T.List[str]) -> int:
    options = parser.parse_args(args)
    langs = options.langs.split('@@') if options.langs else []
    media = options.media.split('@@') if options.media else []
    sources = options.sources.split('@@')
    destdir = os.environ.get('DESTDIR', '')
    src_subdir = os.path.join(os.environ['MESON_SOURCE_ROOT'], options.subdir)
    build_subdir = os.path.join(os.environ['MESON_BUILD_ROOT'], options.subdir)
    abs_sources = [os.path.join(src_subdir, 'C', source) for source in sources]

    if not langs:
        langs = read_linguas(src_subdir)

    if options.command == 'pot':
        build_pot(src_subdir, options.project_id, sources)
    elif options.command == 'update-po':
        build_pot(src_subdir, options.project_id, sources)
        update_po(src_subdir, options.project_id, langs)
    elif options.command == 'build':
        if langs:
            build_translations(src_subdir, build_subdir, langs)
    elif options.command == 'install':
        install_dir = os.path.join(os.environ['MESON_INSTALL_PREFIX'], options.install_dir)
        if langs:
            build_translations(src_subdir, build_subdir, langs)
            merge_translations(build_subdir, abs_sources, langs)
        install_help(src_subdir, build_subdir, sources, media, langs, install_dir,
                     destdir, options.project_id, options.symlinks)
    return 0
