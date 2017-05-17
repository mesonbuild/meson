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

# A tool to run tests in many different ways.

import shlex
import subprocess, sys, os, argparse
import pickle
from mesonbuild import build
from mesonbuild import environment
from mesonbuild.dependencies import ExternalProgram
from mesonbuild import mlog

import time, datetime, multiprocessing, json
import concurrent.futures as conc
import platform
import signal
import random

# GNU autotools interprets a return code of 77 from tests it executes to
# mean that the test should be skipped.
GNU_SKIP_RETURNCODE = 77

def is_windows():
    platname = platform.system().lower()
    return platname == 'windows' or 'mingw' in platname

def is_cygwin():
    platname = platform.system().lower()
    return 'cygwin' in platname

def determine_worker_count():
    varname = 'MESON_TESTTHREADS'
    if varname in os.environ:
        try:
            num_workers = int(os.environ[varname])
        except ValueError:
            print('Invalid value in %s, using 1 thread.' % varname)
            num_workers = 1
    else:
        try:
            # Fails in some weird environments such as Debian
            # reproducible build.
            num_workers = multiprocessing.cpu_count()
        except Exception:
            num_workers = 1
    return num_workers

parser = argparse.ArgumentParser()
parser.add_argument('--repeat', default=1, dest='repeat', type=int,
                    help='Number of times to run the tests.')
parser.add_argument('--no-rebuild', default=False, action='store_true',
                    help='Do not rebuild before running tests.')
parser.add_argument('--gdb', default=False, dest='gdb', action='store_true',
                    help='Run test under gdb.')
parser.add_argument('--list', default=False, dest='list', action='store_true',
                    help='List available tests.')
parser.add_argument('--wrapper', default=None, dest='wrapper', type=shlex.split,
                    help='wrapper to run tests with (e.g. Valgrind)')
parser.add_argument('-C', default='.', dest='wd',
                    help='directory to cd into before running')
parser.add_argument('--suite', default=[], dest='include_suites', action='append', metavar='SUITE',
                    help='Only run tests belonging to the given suite.')
parser.add_argument('--no-suite', default=[], dest='exclude_suites', action='append', metavar='SUITE',
                    help='Do not run tests belonging to the given suite.')
parser.add_argument('--no-stdsplit', default=True, dest='split', action='store_false',
                    help='Do not split stderr and stdout in test logs.')
parser.add_argument('--print-errorlogs', default=False, action='store_true',
                    help="Whether to print failing tests' logs.")
parser.add_argument('--benchmark', default=False, action='store_true',
                    help="Run benchmarks instead of tests.")
parser.add_argument('--logbase', default='testlog',
                    help="Base name for log file.")
parser.add_argument('--num-processes', default=determine_worker_count(), type=int,
                    help='How many parallel processes to use.')
parser.add_argument('-v', '--verbose', default=False, action='store_true',
                    help='Do not redirect stdout and stderr')
parser.add_argument('-q', '--quiet', default=False, action='store_true',
                    help='Produce less output to the terminal.')
parser.add_argument('-t', '--timeout-multiplier', type=float, default=None,
                    help='Define a multiplier for test timeout, for example '
                    ' when running tests in particular conditions they might take'
                    ' more time to execute.')
parser.add_argument('--setup', default=None, dest='setup',
                    help='Which test setup to use.')
parser.add_argument('--test-args', default=[], type=shlex.split,
                    help='Arguments to pass to the specified test(s) or all tests')
parser.add_argument('args', nargs='*',
                    help='Optional list of tests to run')

class TestRun:
    def __init__(self, res, returncode, should_fail, duration, stdo, stde, cmd,
                 env):
        self.res = res
        self.returncode = returncode
        self.duration = duration
        self.stdo = stdo
        self.stde = stde
        self.cmd = cmd
        self.env = env
        self.should_fail = should_fail

    def get_log(self):
        res = '--- command ---\n'
        if self.cmd is None:
            res += 'NONE\n'
        else:
            res += "%s%s\n" % (''.join(["%s='%s' " % (k, v) for k, v in self.env.items()]), ' ' .join(self.cmd))
        if self.stdo:
            res += '--- stdout ---\n'
            res += self.stdo
        if self.stde:
            if res[-1:] != '\n':
                res += '\n'
            res += '--- stderr ---\n'
            res += self.stde
        if res[-1:] != '\n':
            res += '\n'
        res += '-------\n\n'
        return res

def decode(stream):
    if stream is None:
        return ''
    try:
        return stream.decode('utf-8')
    except UnicodeDecodeError:
        return stream.decode('iso-8859-1', errors='ignore')

def write_json_log(jsonlogfile, test_name, result):
    jresult = {'name': test_name,
               'stdout': result.stdo,
               'result': result.res,
               'duration': result.duration,
               'returncode': result.returncode,
               'command': result.cmd}
    if isinstance(result.env, dict):
        jresult['env'] = result.env
    else:
        jresult['env'] = result.env.get_env(os.environ)
    if result.stde:
        jresult['stderr'] = result.stde
    jsonlogfile.write(json.dumps(jresult) + '\n')

def run_with_mono(fname):
    if fname.endswith('.exe') and not (is_windows() or is_cygwin()):
        return True
    return False

class TestHarness:
    def __init__(self, options):
        self.options = options
        self.collected_logs = []
        self.fail_count = 0
        self.success_count = 0
        self.skip_count = 0
        self.timeout_count = 0
        self.is_run = False
        self.tests = None
        self.suites = None
        if self.options.benchmark:
            self.load_datafile(os.path.join(options.wd, 'meson-private', 'meson_benchmark_setup.dat'))
        else:
            self.load_datafile(os.path.join(options.wd, 'meson-private', 'meson_test_setup.dat'))

    def run_single_test(self, wrap, test):
        if test.fname[0].endswith('.jar'):
            cmd = ['java', '-jar'] + test.fname
        elif not test.is_cross and run_with_mono(test.fname[0]):
            cmd = ['mono'] + test.fname
        else:
            if test.is_cross:
                if test.exe_runner is None:
                    # Can not run test on cross compiled executable
                    # because there is no execute wrapper.
                    cmd = None
                else:
                    cmd = [test.exe_runner] + test.fname
            else:
                cmd = test.fname

        if cmd is None:
            res = 'SKIP'
            duration = 0.0
            stdo = 'Not run because can not execute cross compiled binaries.'
            stde = None
            returncode = GNU_SKIP_RETURNCODE
        else:
            cmd = wrap + cmd + test.cmd_args + self.options.test_args
            starttime = time.time()
            child_env = os.environ.copy()
            child_env.update(self.options.global_env.get_env(child_env))
            if isinstance(test.env, build.EnvironmentVariables):
                test.env = test.env.get_env(child_env)

            child_env.update(test.env)
            if len(test.extra_paths) > 0:
                child_env['PATH'] += os.pathsep.join([''] + test.extra_paths)

            # If MALLOC_PERTURB_ is not set, or if it is set to an empty value,
            # (i.e., the test or the environment don't explicitly set it), set
            # it ourselves. We do this unconditionally because it is extremely
            # useful to have in tests.
            # Setting MALLOC_PERTURB_="0" will completely disable this feature.
            if 'MALLOC_PERTURB_' not in child_env or not child_env['MALLOC_PERTURB_']:
                child_env['MALLOC_PERTURB_'] = str(random.randint(1, 255))

            setsid = None
            stdout = None
            stderr = None
            if not self.options.verbose:
                stdout = subprocess.PIPE
                stderr = subprocess.PIPE if self.options and self.options.split else subprocess.STDOUT

                if not is_windows():
                    setsid = os.setsid

            p = subprocess.Popen(cmd,
                                 stdout=stdout,
                                 stderr=stderr,
                                 env=child_env,
                                 cwd=test.workdir,
                                 preexec_fn=setsid)
            timed_out = False
            if test.timeout is None:
                timeout = None
            else:
                timeout = test.timeout * self.options.timeout_multiplier
            try:
                (stdo, stde) = p.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                if self.options.verbose:
                    print("%s time out (After %d seconds)" % (test.name, timeout))
                timed_out = True
                # Python does not provide multiplatform support for
                # killing a process and all its children so we need
                # to roll our own.
                if is_windows():
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(p.pid)])
                else:
                    os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                (stdo, stde) = p.communicate()
            endtime = time.time()
            duration = endtime - starttime
            stdo = decode(stdo)
            if stde:
                stde = decode(stde)
            if timed_out:
                res = 'TIMEOUT'
                self.timeout_count += 1
                self.fail_count += 1
            elif p.returncode == GNU_SKIP_RETURNCODE:
                res = 'SKIP'
                self.skip_count += 1
            elif test.should_fail == bool(p.returncode):
                res = 'OK'
                self.success_count += 1
            else:
                res = 'FAIL'
                self.fail_count += 1
            returncode = p.returncode
        result = TestRun(res, returncode, test.should_fail, duration, stdo, stde, cmd, test.env)

        return result

    def print_stats(self, numlen, tests, name, result, i, logfile, jsonlogfile):
        startpad = ' ' * (numlen - len('%d' % (i + 1)))
        num = '%s%d/%d' % (startpad, i + 1, len(tests))
        padding1 = ' ' * (38 - len(name))
        padding2 = ' ' * (8 - len(result.res))
        result_str = '%s %s  %s%s%s%5.2f s' % \
            (num, name, padding1, result.res, padding2, result.duration)
        if not self.options.quiet or result.res != 'OK':
            if result.res != 'OK' and mlog.colorize_console:
                if result.res == 'FAIL' or result.res == 'TIMEOUT':
                    decorator = mlog.red
                elif result.res == 'SKIP':
                    decorator = mlog.yellow
                else:
                    sys.exit('Unreachable code was ... well ... reached.')
                print(decorator(result_str).get_text(True))
            else:
                print(result_str)
        result_str += "\n\n" + result.get_log()
        if (result.returncode != GNU_SKIP_RETURNCODE) \
                and (result.returncode != 0) != result.should_fail:
            if self.options.print_errorlogs:
                self.collected_logs.append(result_str)
        if logfile:
            logfile.write(result_str)
        if jsonlogfile:
            write_json_log(jsonlogfile, name, result)

    def print_summary(self, logfile):
        msg = '''
OK:      %4d
FAIL:    %4d
SKIP:    %4d
TIMEOUT: %4d
''' % (self.success_count, self.fail_count, self.skip_count, self.timeout_count)
        print(msg)
        if logfile:
            logfile.write(msg)

    def print_collected_logs(self):
        if len(self.collected_logs) > 0:
            if len(self.collected_logs) > 10:
                print('\nThe output from 10 first failed tests:\n')
            else:
                print('\nThe output from the failed tests:\n')
            for log in self.collected_logs[:10]:
                lines = log.splitlines()
                if len(lines) > 104:
                    print('\n'.join(lines[0:4]))
                    print('--- Listing only the last 100 lines from a long log. ---')
                    lines = lines[-100:]
                for line in lines:
                    print(line)

    def doit(self):
        if self.is_run:
            raise RuntimeError('Test harness object can only be used once.')
        if not os.path.isfile(self.datafile):
            print('Test data file. Probably this means that you did not run this in the build directory.')
            return 1
        self.is_run = True
        tests = self.get_tests()
        if not tests:
            return 0
        self.run_tests(tests)
        return self.fail_count

    @staticmethod
    def split_suite_string(suite):
        if ':' in suite:
            return suite.split(':', 1)
        else:
            return suite, ""

    @staticmethod
    def test_in_suites(test, suites):
        for suite in suites:
            (prj_match, st_match) = TestHarness.split_suite_string(suite)
            for prjst in test.suite:
                (prj, st) = TestHarness.split_suite_string(prjst)
                if prj_match and prj != prj_match:
                    continue
                if st_match and st != st_match:
                    continue
                return True
        return False

    def test_suitable(self, test):
        return (not self.options.include_suites or TestHarness.test_in_suites(test, self.options.include_suites)) \
            and not TestHarness.test_in_suites(test, self.options.exclude_suites)

    def load_suites(self):
        ss = set()
        for t in self.tests:
            for s in t.suite:
                ss.add(s)
        self.suites = list(ss)

    def load_tests(self):
        with open(self.datafile, 'rb') as f:
            self.tests = pickle.load(f)

    def load_datafile(self, datafile):
        self.datafile = datafile
        self.load_tests()
        self.load_suites()

    def get_tests(self):
        if not self.tests:
            print('No tests defined.')
            return []

        if len(self.options.include_suites) or len(self.options.exclude_suites):
            tests = []
            for tst in self.tests:
                if self.test_suitable(tst):
                    tests.append(tst)
        else:
            tests = self.tests

        if self.options.args:
            tests = [t for t in tests if t.name in self.options.args]

        if not tests:
            print('No suitable tests defined.')
            return []

        for test in tests:
            test.rebuilt = False

        return tests

    def open_log_files(self):
        if not self.options.logbase or self.options.verbose:
            return None, None, None, None

        namebase = None
        logfile_base = os.path.join(self.options.wd, 'meson-logs', self.options.logbase)

        if self.options.wrapper:
            namebase = os.path.split(self.get_wrapper()[0])[1]
        elif self.options.setup:
            namebase = self.options.setup

        if namebase:
            logfile_base += '-' + namebase.replace(' ', '_')
        logfilename = logfile_base + '.txt'
        jsonlogfilename = logfile_base + '.json'

        jsonlogfile = open(jsonlogfilename, 'w')
        logfile = open(logfilename, 'w')

        logfile.write('Log of Meson test suite run on %s\n\n'
                      % datetime.datetime.now().isoformat())

        return logfile, logfilename, jsonlogfile, jsonlogfilename

    def get_wrapper(self):
        wrap = []
        if self.options.gdb:
            wrap = ['gdb', '--quiet', '--nh']
            if self.options.repeat > 1:
                wrap += ['-ex', 'run', '-ex', 'quit']
            # Signal the end of arguments to gdb
            wrap += ['--args']
        if self.options.wrapper:
            wrap += self.options.wrapper
        assert(isinstance(wrap, list))
        return wrap

    def get_pretty_suite(self, test):
        if len(self.suites) > 1:
            rv = TestHarness.split_suite_string(test.suite[0])[0]
            s = "+".join(TestHarness.split_suite_string(s)[1] for s in test.suite)
            if len(s):
                rv += ":"
            return rv + s + " / " + test.name
        else:
            return test.name

    def run_tests(self, tests):
        executor = None
        logfile = None
        jsonlogfile = None
        futures = []
        try:
            numlen = len('%d' % len(tests))
            (logfile, logfilename, jsonlogfile, jsonlogfilename) = self.open_log_files()
            wrap = self.get_wrapper()

            for _ in range(self.options.repeat):
                for i, test in enumerate(tests):
                    visible_name = self.get_pretty_suite(test)

                    if self.options.gdb:
                        test.timeout = None

                    if not test.is_parallel or self.options.gdb:
                        self.drain_futures(futures)
                        futures = []
                        res = self.run_single_test(wrap, test)
                        self.print_stats(numlen, tests, visible_name, res, i, logfile, jsonlogfile)
                    else:
                        if not executor:
                            executor = conc.ThreadPoolExecutor(max_workers=self.options.num_processes)
                        f = executor.submit(self.run_single_test, wrap, test)
                        futures.append((f, numlen, tests, visible_name, i, logfile, jsonlogfile))
                    if self.options.repeat > 1 and self.fail_count:
                        break
                if self.options.repeat > 1 and self.fail_count:
                    break

            self.drain_futures(futures)
            self.print_summary(logfile)
            self.print_collected_logs()

            if logfilename:
                print('Full log written to %s' % logfilename)
        finally:
            if jsonlogfile:
                jsonlogfile.close()
            if logfile:
                logfile.close()

    def drain_futures(self, futures):
        for i in futures:
            (result, numlen, tests, name, i, logfile, jsonlogfile) = i
            if self.options.repeat > 1 and self.fail_count:
                result.cancel()
            if self.options.verbose:
                result.result()
            self.print_stats(numlen, tests, name, result.result(), i, logfile, jsonlogfile)

    def run_special(self):
        'Tests run by the user, usually something like "under gdb 1000 times".'
        if self.is_run:
            raise RuntimeError('Can not use run_special after a full run.')
        if os.path.isfile('build.ninja'):
            subprocess.check_call([environment.detect_ninja(), 'all'])
        tests = self.get_tests()
        if not tests:
            return 0
        self.run_tests(tests)
        return self.fail_count


def list_tests(th):
    tests = th.get_tests()
    for t in tests:
        print(th.get_pretty_suite(t))

def merge_suite_options(options):
    buildfile = os.path.join(options.wd, 'meson-private/build.dat')
    with open(buildfile, 'rb') as f:
        build = pickle.load(f)
    setups = build.test_setups
    if options.setup not in setups:
        sys.exit('Unknown test setup: %s' % options.setup)
    current = setups[options.setup]
    if not options.gdb:
        options.gdb = current.gdb
    if options.timeout_multiplier is None:
        options.timeout_multiplier = current.timeout_multiplier
#    if options.env is None:
#        options.env = current.env # FIXME, should probably merge options here.
    if options.wrapper is not None and current.exe_wrapper is not None:
        sys.exit('Conflict: both test setup and command line specify an exe wrapper.')
    if options.wrapper is None:
        options.wrapper = current.exe_wrapper
    return current.env

def rebuild_all(wd):
    if not os.path.isfile(os.path.join(wd, 'build.ninja')):
        print("Only ninja backend is supported to rebuild tests before running them.")
        return True

    ninja = environment.detect_ninja()
    if not ninja:
        print("Can't find ninja, can't rebuild test.")
        return False

    p = subprocess.Popen([ninja, '-C', wd])
    p.communicate()

    if p.returncode != 0:
        print("Could not rebuild")
        return False

    return True

def run(args):
    options = parser.parse_args(args)

    if options.benchmark:
        options.num_processes = 1

    if options.setup is not None:
        global_env = merge_suite_options(options)
    else:
        global_env = build.EnvironmentVariables()
        if options.timeout_multiplier is None:
            options.timeout_multiplier = 1

    setattr(options, 'global_env', global_env)

    if options.verbose and options.quiet:
        print('Can not be both quiet and verbose at the same time.')
        return 1

    check_bin = None
    if options.gdb:
        options.verbose = True
        if options.wrapper:
            print('Must not specify both a wrapper and gdb at the same time.')
            return 1
        check_bin = 'gdb'

    if options.wrapper:
        check_bin = options.wrapper[0]

    if check_bin is not None:
        exe = ExternalProgram(check_bin, silent=True)
        if not exe.found():
            sys.exit("Could not find requested program: %s" % check_bin)
    options.wd = os.path.abspath(options.wd)

    if not options.no_rebuild:
        if not rebuild_all(options.wd):
            sys.exit(-1)

    th = TestHarness(options)
    if options.list:
        list_tests(th)
        return 0
    if not options.args:
        return th.doit()
    return th.run_special()

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
