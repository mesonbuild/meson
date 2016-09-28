#!/usr/bin/env python3
# Copyright 2015-2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os
import subprocess
import shutil
import argparse
from mesonbuild.mesonlib import MesonException
from mesonbuild.scripts import destdir_join

parser = argparse.ArgumentParser()

parser.add_argument('--sourcedir', dest='sourcedir')
parser.add_argument('--builddir', dest='builddir')
parser.add_argument('--subdir', dest='subdir')
parser.add_argument('--headerdir', dest='headerdir')
parser.add_argument('--mainfile', dest='mainfile')
parser.add_argument('--modulename', dest='modulename')
parser.add_argument('--htmlargs', dest='htmlargs', default='')
parser.add_argument('--scanargs', dest='scanargs', default='')
parser.add_argument('--scanobjsargs', dest='scanobjsargs', default='')
parser.add_argument('--gobjects-types-file', dest='gobject_typesfile', default='')
parser.add_argument('--fixxrefargs', dest='fixxrefargs', default='')
parser.add_argument('--ld', dest='ld', default='')
parser.add_argument('--cc', dest='cc', default='')
parser.add_argument('--ldflags', dest='ldflags', default='')
parser.add_argument('--cflags', dest='cflags', default='')
parser.add_argument('--content-files', dest='content_files', default='')
parser.add_argument('--html-assets', dest='html_assets', default='')
parser.add_argument('--installdir', dest='install_dir')

def gtkdoc_run_check(cmd, cwd):
    p = subprocess.Popen(cmd, cwd=cwd,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stde, stdo) = p.communicate()
    if p.returncode != 0:
        err_msg = ["{!r} failed with status {:d}".format(cmd[0], p.returncode)]
        if stde:
            err_msg.append(stde.decode(errors='ignore'))
        if stdo:
            err_msg.append(stdo.decode(errors='ignore'))
        raise MesonException('\n'.join(err_msg))

def build_gtkdoc(source_root, build_root, doc_subdir, src_subdir,
                 main_file, module, html_args, scan_args, fixxref_args,
                 gobject_typesfile, scanobjs_args, ld, cc, ldflags, cflags,
                 html_assets, content_files):
    print("Building documentation for %s" % module)

    abs_src = os.path.join(source_root, src_subdir)
    doc_src = os.path.join(source_root, doc_subdir)
    abs_out = os.path.join(build_root, doc_subdir)
    htmldir = os.path.join(abs_out, 'html')

    content_files += [main_file]
    sections = os.path.join(doc_src, module + "-sections.txt")
    if os.path.exists(sections):
        content_files.append(sections)

    # Copy files to build directory
    for f in content_files:
        f_abs = os.path.join(doc_src, f)
        shutil.copyfile(f_abs, os.path.join(
            abs_out, os.path.basename(f_abs)))

    shutil.rmtree(htmldir, ignore_errors=True)
    try:
        os.mkdir(htmldir)
    except Exception:
        pass

    for f in html_assets:
        f_abs = os.path.join(doc_src, f)
        shutil.copyfile(f_abs, os.path.join(htmldir, os.path.basename(f_abs)))

    scan_cmd = ['gtkdoc-scan',
                '--module=' + module,
                '--source-dir=' + abs_src] + scan_args
    gtkdoc_run_check(scan_cmd, abs_out)

    if gobject_typesfile:
        scanobjs_cmd = ['gtkdoc-scangobj'] + scanobjs_args + [gobject_typesfile,
            '--module=' + module, '--cflags=' + cflags, '--ldflags=' + ldflags]

        gtkdoc_run_check(scanobjs_cmd, abs_out)


    # Make docbook files
    if main_file.endswith('sgml'):
        modeflag = '--sgml-mode'
    else:
        modeflag = '--xml-mode'
    mkdb_cmd = ['gtkdoc-mkdb',
                '--module=' + module,
                '--output-format=xml',
                '--expand-content-files=',
                modeflag,
                '--source-dir=' + abs_src]
    if len(main_file) > 0:
        # Yes, this is the flag even if the file is in xml.
        mkdb_cmd.append('--main-sgml-file=' + main_file)
    gtkdoc_run_check(mkdb_cmd, abs_out)

    # Make HTML documentation
    mkhtml_cmd = ['gtkdoc-mkhtml',
                  '--path=' + abs_src,
                  module,
                  ] + html_args
    if len(main_file) > 0:
        mkhtml_cmd.append('../' + main_file)
    else:
        mkhtml_cmd.append('%s-docs.xml' % module)
    # html gen must be run in the HTML dir
    gtkdoc_run_check(mkhtml_cmd, os.path.join(abs_out, 'html'))

    # Fix cross-references in HTML files
    fixref_cmd = ['gtkdoc-fixxref',
                  '--module=' + module,
                  '--module-dir=html'] + fixxref_args
    gtkdoc_run_check(fixref_cmd, abs_out)

def install_gtkdoc(build_root, doc_subdir, install_prefix, datadir, module):
    source = os.path.join(build_root, doc_subdir, 'html')
    final_destination = os.path.join(install_prefix, datadir, module)
    shutil.rmtree(final_destination, ignore_errors=True)
    shutil.copytree(source, final_destination)

def run(args):
    options = parser.parse_args(args)
    if len(options.htmlargs) > 0:
        htmlargs = options.htmlargs.split('@@')
    else:
        htmlargs = []
    if len(options.scanargs) > 0:
        scanargs = options.scanargs.split('@@')
    else:
        scanargs = []
    if len(options.scanobjsargs) > 0:
        scanobjsargs = options.scanobjsargs.split('@@')
    else:
        scanobjsargs = []
    if len(options.fixxrefargs) > 0:
        fixxrefargs = options.fixxrefargs.split('@@')
    else:
        fixxrefargs = []
    build_gtkdoc(
        options.sourcedir,
        options.builddir,
        options.subdir,
        options.headerdir,
        options.mainfile,
        options.modulename,
        htmlargs,
        scanargs,
        fixxrefargs,
        options.gobject_typesfile,
        scanobjsargs,
        options.ld,
        options.cc,
        options.ldflags,
        options.cflags,
        options.html_assets.split('@@') if options.html_assets else [],
        options.content_files.split('@@') if options.content_files else [])

    if 'MESON_INSTALL_PREFIX' in os.environ:
        install_dir = options.install_dir if options.install_dir else options.modulename
        destdir = os.environ.get('DESTDIR', '')
        installdir = destdir_join(destdir, os.environ['MESON_INSTALL_PREFIX'])
        install_gtkdoc(options.builddir,
                       options.subdir,
                       installdir,
                       'share/gtk-doc/html',
                       install_dir)
    return 0

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
