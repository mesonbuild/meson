# Copyright 2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mesonbuild import environment

import argparse, sys, os, subprocess, pathlib

def coverage(outputs, source_root, subproject_root, build_root, log_dir):
    outfiles = []
    exitcode = 0

    (gcovr_exe, gcovr_new_rootdir, lcov_exe, genhtml_exe) = environment.find_coverage_tools()

    # gcovr >= 3.1 interprets rootdir differently
    if gcovr_new_rootdir:
        gcovr_rootdir = build_root
    else:
        gcovr_rootdir = source_root

    if not outputs or 'xml' in outputs:
        if gcovr_exe:
            subprocess.check_call([gcovr_exe,
                                   '-x',
                                   '-r', gcovr_rootdir,
                                   '-e', subproject_root,
                                   '-o', os.path.join(log_dir, 'coverage.xml'),
                                   ])
            outfiles.append(('Xml', pathlib.Path(log_dir, 'coverage.xml')))
        elif outputs:
            print('gcovr needed to generate Xml coverage report')
            exitcode = 1

    if not outputs or 'text' in outputs:
        if gcovr_exe:
            subprocess.check_call([gcovr_exe,
                                   '-r', gcovr_rootdir,
                                   '-e', subproject_root,
                                   '-o', os.path.join(log_dir, 'coverage.txt'),
                                   ])
            outfiles.append(('Text', pathlib.Path(log_dir, 'coverage.txt')))
        elif outputs:
            print('gcovr needed to generate text coverage report')
            exitcode = 1

    if not outputs or 'html' in outputs:
        if lcov_exe and genhtml_exe:
            htmloutdir = os.path.join(log_dir, 'coveragereport')
            covinfo = os.path.join(log_dir, 'coverage.info')
            initial_tracefile = covinfo + '.initial'
            run_tracefile = covinfo + '.run'
            raw_tracefile = covinfo + '.raw'
            subprocess.check_call([lcov_exe,
                                   '--directory', build_root,
                                   '--capture',
                                   '--initial',
                                   '--output-file',
                                   initial_tracefile])
            subprocess.check_call([lcov_exe,
                                   '--directory', build_root,
                                   '--capture',
                                   '--output-file', run_tracefile,
                                   '--no-checksum',
                                   '--rc', 'lcov_branch_coverage=1',
                                   ])
            # Join initial and test results.
            subprocess.check_call([lcov_exe,
                                   '-a', initial_tracefile,
                                   '-a', run_tracefile,
                                   '-o', raw_tracefile])
            # Remove all directories outside the source_root from the covinfo
            subprocess.check_call([lcov_exe,
                                   '--extract', raw_tracefile,
                                   os.path.join(source_root, '*'),
                                   '--output-file', covinfo])
            # Remove all directories inside subproject dir
            subprocess.check_call([lcov_exe,
                                   '--remove', covinfo,
                                   os.path.join(subproject_root, '*'),
                                   '--output-file', covinfo])
            subprocess.check_call([genhtml_exe,
                                   '--prefix', build_root,
                                   '--output-directory', htmloutdir,
                                   '--title', 'Code coverage',
                                   '--legend',
                                   '--show-details',
                                   '--branch-coverage',
                                   covinfo])
            outfiles.append(('Html', pathlib.Path(htmloutdir, 'index.html')))
        elif gcovr_exe and gcovr_new_rootdir:
            htmloutdir = os.path.join(log_dir, 'coveragereport')
            if not os.path.isdir(htmloutdir):
                os.mkdir(htmloutdir)
            subprocess.check_call([gcovr_exe,
                                   '--html',
                                   '--html-details',
                                   '-r', build_root,
                                   '-e', subproject_root,
                                   '-o', os.path.join(htmloutdir, 'index.html'),
                                   ])
            outfiles.append(('Html', pathlib.Path(htmloutdir, 'index.html')))
        elif outputs:
            print('lcov/genhtml or gcovr >= 3.1 needed to generate Html coverage report')
            exitcode = 1

    if not outputs and not outfiles:
        print('Need gcovr or lcov/genhtml to generate any coverage reports')
        exitcode = 1

    if outfiles:
        print('')
        for (filetype, path) in outfiles:
            print(filetype + ' coverage report can be found at', path.as_uri())

    return exitcode

def run(args):
    if not os.path.isfile('build.ninja'):
        print('Coverage currently only works with the Ninja backend.')
        return 1
    parser = argparse.ArgumentParser(description='Generate coverage reports')
    parser.add_argument('--text', dest='outputs', action='append_const',
                        const='text', help='generate Text report')
    parser.add_argument('--xml', dest='outputs', action='append_const',
                        const='xml', help='generate Xml report')
    parser.add_argument('--html', dest='outputs', action='append_const',
                        const='html', help='generate Html report')
    parser.add_argument('source_root')
    parser.add_argument('subproject_root')
    parser.add_argument('build_root')
    parser.add_argument('log_dir')
    options = parser.parse_args(args)
    return coverage(options.outputs, options.source_root,
                    options.subproject_root, options.build_root,
                    options.log_dir)

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
