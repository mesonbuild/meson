# SPDX-License-Identifier: Apache-2.0
# Copyright 2017 The Meson development team

from __future__ import annotations

from mesonbuild import tooldetect, mesonlib

import argparse, re, sys, os, subprocess, pathlib, stat, shutil
import typing as T

def coverage(outputs: T.List[str], source_root: str, subproject_root: str, build_root: str, log_dir: str, use_llvm_cov: bool,
             gcovr_exe: str, llvm_cov_exe: str) -> int:
    outfiles = []
    exitcode = 0

    if gcovr_exe == '':
        gcovr_exe = None
    else:
        gcovr_exe, gcovr_version = tooldetect.detect_gcovr(gcovr_exe)
    if llvm_cov_exe == '' or shutil.which(llvm_cov_exe) is None:
        llvm_cov_exe = None

    lcov_exe, lcov_version, genhtml_exe = tooldetect.detect_lcov_genhtml()

    # load config files for tools if available in the source tree
    # - lcov requires manually specifying a per-project config
    # - gcovr picks up the per-project config, and also supports filtering files
    #   so don't exclude subprojects ourselves, if the project has a config,
    #   because they either don't want that, or should set it themselves
    lcovrc = os.path.join(source_root, '.lcovrc')
    if os.path.exists(lcovrc):
        lcov_config = ['--config-file', lcovrc]
    else:
        lcov_config = []

    if lcov_exe and mesonlib.version_compare(lcov_version, '>=2.0'):
        lcov_exe_rc_branch_coverage = ['--rc', 'branch_coverage=1']
    else:
        lcov_exe_rc_branch_coverage = ['--rc', 'lcov_branch_coverage=1']

    gcovr_config = ['-e', re.escape(subproject_root)]

    # gcovr >= 4.2 requires a different syntax for out of source builds
    if gcovr_exe and mesonlib.version_compare(gcovr_version, '>=4.2'):
        gcovr_base_cmd = [gcovr_exe, '-r', source_root, build_root]
        # it also started supporting the config file
        if os.path.exists(os.path.join(source_root, 'gcovr.cfg')):
            gcovr_config = []
    else:
        gcovr_base_cmd = [gcovr_exe, '-r', build_root]

    if gcovr_exe and mesonlib.version_compare(gcovr_version, '>=5.2'):
        gcovr_base_cmd.append('-j')

    if use_llvm_cov:
        gcov_exe_args = ['--gcov-executable', llvm_cov_exe + ' gcov']
    else:
        gcov_exe_args = []

    if gcovr_exe:
        gcovr_targets = [x for x in mesonlib.GCOVR_COVERAGE_TARGETS if mesonlib.version_compare(gcovr_version, x.version_requirement)]
        if outputs:
            gcovr_targets = [x for x in gcovr_targets if x.pretty_name in outputs]

        # The --txt option did not exist up until 5.0
        if not mesonlib.version_compare(gcovr_version, '>=5.0'):
            len_pre = len(gcovr_targets)
            gcovr_targets = [x for x in gcovr_targets if x.pretty_name != 'text']
            if len_pre > len(gcovr_targets):
                subprocess.check_call(gcovr_base_cmd + gcovr_config + ['-o', os.path.join(log_dir, 'coverage.txt')] + gcov_exe_args)
                outfiles.append(('text', pathlib.Path(log_dir, 'coverage.txt')))

        # Generate all report types in one invocation
        args = [x for pair in [[x.gcovr_argument, os.path.join(log_dir, x.output_file)] for x in gcovr_targets] for x in pair]

        if (not outputs or 'html' in outputs) and mesonlib.version_compare(gcovr_version, '>=3.3'):
            htmloutdir = os.path.join(log_dir, 'coveragereport')
            os.makedirs(htmloutdir, exist_ok=True)
            # Use `--html-details` if gcovr version < 6.0, otherwise
            # use `--html-nested`.
            html_arg = '--html-details'
            if mesonlib.version_compare(gcovr_version, '>=6.0'):
                html_arg = '--html-nested'
            args += [html_arg, os.path.join(htmloutdir, 'index.html')]
            outfiles.append(('Html', pathlib.Path(htmloutdir, 'index.html')))

        subprocess.check_call(gcovr_base_cmd + gcovr_config + args + gcov_exe_args)
        for target in gcovr_targets:
            outfiles.append((target.pretty_name.capitalize(), pathlib.Path(log_dir, target.output_file)))

    if not gcovr_exe:
        if (not outputs or 'html' in outputs) and (lcov_exe and genhtml_exe):
            htmloutdir = os.path.join(log_dir, 'coveragereport')
            covinfo = os.path.join(log_dir, 'coverage.info')
            initial_tracefile = covinfo + '.initial'
            run_tracefile = covinfo + '.run'
            raw_tracefile = covinfo + '.raw'
            lcov_subpoject_exclude = []
            if os.path.exists(subproject_root):
                lcov_subpoject_exclude.append(os.path.join(subproject_root, '*'))
            if use_llvm_cov:
                # Create a shim to allow using llvm-cov as a gcov tool.
                if mesonlib.is_windows():
                    llvm_cov_shim_path = os.path.join(log_dir, 'llvm-cov.bat')
                    with open(llvm_cov_shim_path, 'w', encoding='utf-8') as llvm_cov_bat:
                        llvm_cov_bat.write(f'@"{llvm_cov_exe}" gcov %*')
                else:
                    llvm_cov_shim_path = os.path.join(log_dir, 'llvm-cov.sh')
                    with open(llvm_cov_shim_path, 'w', encoding='utf-8') as llvm_cov_sh:
                        llvm_cov_sh.write(f'#!/usr/bin/env sh\nexec "{llvm_cov_exe}" gcov $@')
                    os.chmod(llvm_cov_shim_path, os.stat(llvm_cov_shim_path).st_mode | stat.S_IEXEC)
                gcov_tool_args = ['--gcov-tool', llvm_cov_shim_path]
            else:
                gcov_tool_args = []
            subprocess.check_call([lcov_exe,
                                   '--directory', build_root,
                                   '--capture',
                                   '--initial',
                                   '--output-file',
                                   initial_tracefile] +
                                  lcov_config +
                                  gcov_tool_args)
            subprocess.check_call([lcov_exe,
                                   '--directory', build_root,
                                   '--capture',
                                   '--output-file', run_tracefile,
                                   '--no-checksum',
                                   *lcov_exe_rc_branch_coverage] +
                                  lcov_config +
                                  gcov_tool_args)
            # Join initial and test results.
            subprocess.check_call([lcov_exe,
                                   '-a', initial_tracefile,
                                   '-a', run_tracefile,
                                   *lcov_exe_rc_branch_coverage,
                                   '-o', raw_tracefile] + lcov_config)
            # Remove all directories outside the source_root from the covinfo
            subprocess.check_call([lcov_exe,
                                   '--extract', raw_tracefile,
                                   os.path.join(source_root, '*'),
                                   *lcov_exe_rc_branch_coverage,
                                   '--output-file', covinfo] + lcov_config)
            # Remove all directories inside subproject dir
            subprocess.check_call([lcov_exe,
                                   '--remove', covinfo,
                                   *lcov_subpoject_exclude,
                                   *lcov_exe_rc_branch_coverage,
                                   '--ignore-errors', 'unused',
                                   '--output-file', covinfo] + lcov_config)
            subprocess.check_call([genhtml_exe,
                                   '--prefix', build_root,
                                   '--prefix', source_root,
                                   '--output-directory', htmloutdir,
                                   '--title', 'Code coverage',
                                   '--legend',
                                   '--show-details',
                                   '--branch-coverage',
                                   covinfo] + lcov_config)
            outfiles.append(('Html', pathlib.Path(htmloutdir, 'index.html')))
        elif outputs:
            print('lcov/genhtml or gcovr >= 3.3 needed to generate Html coverage report')
            exitcode = 1

    if not outputs and not outfiles:
        print('Need gcovr or lcov/genhtml to generate any coverage reports')
        exitcode = 1

    if outfiles:
        print('')
        for (filetype, path) in outfiles:
            print(filetype + ' coverage report can be found at', path.as_uri())

    return exitcode

def run(args: T.List[str]) -> int:
    if not os.path.isfile('build.ninja'):
        print('Coverage currently only works with the Ninja backend.')
        return 1
    parser = argparse.ArgumentParser(description='Generate coverage reports')
    for target in mesonlib.GCOVR_COVERAGE_TARGETS:
        parser.add_argument(target.gcovr_argument, dest='outputs', action='append_const',
                            const=target.pretty_name,
                            help=f'generate {target.pretty_name.capitalize()} coverage report')
    parser.add_argument('--html', dest='outputs', action='append_const',
                        const='html', help='generate Html coverage report')
    parser.add_argument('--use-llvm-cov', action='store_true',
                        help='use llvm-cov')
    parser.add_argument('--gcovr', action='store', default='',
                        help='The gcovr executable to use if specified')
    parser.add_argument('--llvm-cov', action='store', default='',
                        help='The llvm-cov executable to use if specified')
    parser.add_argument('source_root')
    parser.add_argument('subproject_root')
    parser.add_argument('build_root')
    parser.add_argument('log_dir')
    options = parser.parse_args(args)
    return coverage(options.outputs, options.source_root,
                    options.subproject_root, options.build_root,
                    options.log_dir, options.use_llvm_cov,
                    options.gcovr, options.llvm_cov)

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
