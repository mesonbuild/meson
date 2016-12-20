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

import subprocess, sys, os, argparse
import pickle
from mesonbuild import build
from mesonbuild import environment

import time, datetime, multiprocessing, json
import concurrent.futures as conc
import platform
import signal

# GNU autotools interprets a return code of 77 from tests it executes to
# mean that the test should be skipped.
GNU_SKIP_RETURNCODE = 77

def is_windows():
    platname = platform.system().lower()
    return platname == 'windows' or 'mingw' in platname

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
parser.add_argument('--wrapper', default=None, dest='wrapper',
                    help='wrapper to run tests with (e.g. Valgrind)')
parser.add_argument('-C', default='.', dest='wd',
                    help='directory to cd into before running')
parser.add_argument('--suite', default=None, dest='suite',
                    help='Only run tests belonging to the given suite.')
parser.add_argument('--no-stdsplit', default=True, dest='split', action='store_false',
                    help='Do not split stderr and stdout in test logs.')
parser.add_argument('--print-errorlogs', default=False, action='store_true',
                    help="Whether to print faling tests' logs.")
parser.add_argument('--benchmark', default=False, action='store_true',
                    help="Run benchmarks instead of tests.")
parser.add_argument('--logbase', default='testlog',
                    help="Base name for log file.")
parser.add_argument('--num-processes', default=determine_worker_count(), type=int,
                    help='How many parallel processes to use.')
parser.add_argument('-v', '--verbose', default=False, action='store_true',
                    help='Do not redirect stdout and stderr')
parser.add_argument('-t', '--timeout-multiplier', type=float, default=1.0,
                    help='Define a multiplier for test timeout, for example '
                    ' when running tests in particular conditions they might take'
                    ' more time to execute.')
parser.add_argument('args', nargs='*')

class TestRun():
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
            res += "\n%s %s\n" %(' '.join(
                ["%s='%s'" % (k, v) for k, v in self.env.items()]),
                ' ' .join(self.cmd))
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
    jresult = {'name' : test_name,
              'stdout' : result.stdo,
              'result' : result.res,
              'duration' : result.duration,
              'returncode' : result.returncode,
              'command' : result.cmd,
              }
    if isinstance(result.env, dict):
        jresult['env'] = result.env
    else:
        jresult['env'] = result.env.get_env(os.environ)
    if result.stde:
        jresult['stderr'] = result.stde
    jsonlogfile.write(json.dumps(jresult) + '\n')

def run_with_mono(fname):
    if fname.endswith('.exe') and not is_windows():
        return True
    return False

class TestHarness:
    def __init__(self, options):
        self.options = options
        self.collected_logs = []
        self.failed_tests = []
        self.error_count = 0
        self.is_run = False
        self.cant_rebuild = False
        if self.options.benchmark:
            self.datafile = os.path.join(options.wd, 'meson-private/meson_benchmark_setup.dat')
        else:
            self.datafile = os.path.join(options.wd, 'meson-private/meson_test_setup.dat')

    def rebuild_all(self):
        if not os.path.isfile(os.path.join(self.options.wd, 'build.ninja')):
            print("Only ninja backend is supported to rebuilt tests before running them.")
            self.cant_rebuild = True
            return True

        ninja = environment.detect_ninja()
        if not ninja:
            print("Can't find ninja, can't rebuild test.")
            self.cant_rebuild = True
            return False

        p = subprocess.Popen([ninja, '-C', self.options.wd])
        (stdo, stde) = p.communicate()

        if p.returncode != 0:
            print("Could not rebuild")
            return False

        return True

    def run_single_test(self, wrap, test):
        failling = False
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
            cmd = wrap + cmd + test.cmd_args
            starttime = time.time()
            child_env = os.environ.copy()
            if isinstance(test.env, build.EnvironmentVariables):
                test.env = test.env.get_env(child_env)

            child_env.update(test.env)
            if len(test.extra_paths) > 0:
                child_env['PATH'] = child_env['PATH'] + ';'.join([''] + test.extra_paths)

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
                failling = True
            if p.returncode == GNU_SKIP_RETURNCODE:
                res = 'SKIP'
            elif (not test.should_fail and p.returncode == 0) or \
                (test.should_fail and p.returncode != 0):
                res = 'OK'
            else:
                res = 'FAIL'
                failling = True
            returncode = p.returncode
        result = TestRun(res, returncode, test.should_fail, duration, stdo, stde, cmd, test.env)

        if failling:
            self.failed_tests.append(result)

        return result

    def print_stats(self, numlen, tests, name, result, i, logfile, jsonlogfile):
        startpad = ' '*(numlen - len('%d' % (i+1)))
        num = '%s%d/%d' % (startpad, i+1, len(tests))
        padding1 = ' '*(38-len(name))
        padding2 = ' '*(8-len(result.res))
        result_str = '%s %s  %s%s%s%5.2f s' % \
            (num, name, padding1, result.res, padding2, result.duration)
        print(result_str)
        result_str += "\n\n" + result.get_log()
        if (result.returncode != GNU_SKIP_RETURNCODE) and \
            (result.returncode != 0) != result.should_fail:
            self.error_count += 1
            if self.options.print_errorlogs:
                self.collected_logs.append(result_str)
        logfile.write(result_str)
        write_json_log(jsonlogfile, name, result)

    def doit(self):
        if self.is_run:
            raise RuntimeError('Test harness object can only be used once.')
        if not os.path.isfile(self.datafile):
            print('Test data file. Probably this means that you did not run this in the build directory.')
            return 1
        self.is_run = True
        logfilename = self.run_tests(self.options.logbase)
        if len(self.collected_logs) > 0:
            if len(self.collected_logs) > 10:
                print('\nThe output from 10 first failed tests:\n')
            else:
                print('\nThe output from the failed tests:\n')
            for log in self.collected_logs[:10]:
                lines = log.splitlines()
                if len(lines) > 100:
                    print(lines[0])
                    print('--- Listing only the last 100 lines from a long log. ---')
                    lines = lines[-99:]
                for line in lines:
                    print(line)
        print('Full log written to %s.' % logfilename)
        return self.error_count

    def get_tests(self):
        with open(self.datafile, 'rb') as f:
            tests = pickle.load(f)
        for test in tests:
            test.rebuilt = False

        return tests

    def run_tests(self, log_base):
        logfile_base = os.path.join(self.options.wd, 'meson-logs', log_base)
        if self.options.wrapper is None:
            wrap = []
            logfilename = logfile_base + '.txt'
            jsonlogfilename = logfile_base+ '.json'
        else:
            wrap = self.options.wrapper.split()
            namebase = wrap[0]
            logfilename = logfile_base + '-' + namebase.replace(' ', '_') + '.txt'
            jsonlogfilename = logfile_base + '-' + namebase.replace(' ', '_') + '.json'
        tests = self.get_tests()
        if len(tests) == 0:
            print('No tests defined.')
            return
        numlen = len('%d' % len(tests))
        executor = conc.ThreadPoolExecutor(max_workers=self.options.num_processes)
        futures = []
        filtered_tests = filter_tests(self.options.suite, tests)

        jsonlogfile = None
        logfile = None
        try:
            if not self.options.verbose:
                jsonlogfile =  open(jsonlogfilename, 'w')
                logfile = open(logfilename, 'w')
                logfile.write('Log of Meson test suite run on %s.\n\n' %
                            datetime.datetime.now().isoformat())

            for i in range(self.options.repeat):
                for i, test in enumerate(filtered_tests):
                    if test.suite[0] == '':
                        visible_name = test.name
                    else:
                        if self.options.suite is not None:
                            visible_name = self.options.suite + ' / ' + test.name
                        else:
                            visible_name = test.suite[0] + ' / ' + test.name

                    if not test.is_parallel:
                        self.drain_futures(futures)
                        futures = []
                        res = self.run_single_test(wrap, test)
                        if not self.options.verbose:
                            self.print_stats(numlen, filtered_tests, visible_name, res, i,
                                            logfile, jsonlogfile)
                    else:
                        f = executor.submit(self.run_single_test, wrap, test)
                        if not self.options.verbose:
                            futures.append((f, numlen, filtered_tests, visible_name, i,
                                            logfile, jsonlogfile))
            self.drain_futures(futures, logfile, jsonlogfile)
        finally:
            if jsonlogfile:
                jsonlogfile.close()
            if logfile:
                logfile.close()

        return logfilename


    def drain_futures(self, futures, logfile, jsonlogfile):
        for i in futures:
            (result, numlen, tests, name, i, logfile, jsonlogfile) = i
            if self.options.repeat > 1 and self.failed_tests:
                result.cancel()
            elif not self.options.verbose:
                self.print_stats(numlen, tests, name, result.result(), i, logfile, jsonlogfile)
            else:
                result.result()

        if self.options.repeat > 1 and self.failed_tests:
            if not self.options.verbose:
                for res in self.failed_tests:
                    print('Test failed:\n\n-- stdout --\n')
                    print(res.stdo)
                    print('\n-- stderr --\n')
                    print(res.stde)
                    return 1

            return

    def run_special(self):
        'Tests run by the user, usually something like "under gdb 1000 times".'
        if self.is_run:
            raise RuntimeError('Can not use run_special after a full run.')
        if self.options.wrapper is not None:
            wrap = self.options.wrapper.split(' ')
        else:
            wrap = []
        if self.options.gdb and len(wrap) > 0:
            print('Can not specify both a wrapper and gdb.')
            return 1
        if os.path.isfile('build.ninja'):
            subprocess.check_call([environment.detect_ninja(), 'all'])
        tests = self.get_tests()
        if self.options.list:
            for i in tests:
                print(i.name)
            return 0
        for t in tests:
            if t.name in self.options.args:
                for i in range(self.options.repeat):
                    print('Running: %s %d/%d' % (t.name, i+1, self.options.repeat))
                    if self.options.gdb:
                        wrap = ['gdb', '--quiet']
                        if len(t.cmd_args) > 0:
                            wrap.append('--args')
                        if self.options.repeat > 1:
                            # The user wants to debug interactively, so no timeout.
                            t.timeout = None
                            wrap += ['-ex', 'run', '-ex', 'quit']

                        res = self.run_single_test(wrap, t)
                    else:
                        res = self.run_single_test(wrap, t)
                        if (res.returncode == 0 and res.should_fail) or \
                                (res.returncode != 0 and not res.should_fail):
                            if not self.options.verbose:
                                print('Test failed:\n\n-- stdout --\n')
                                print(res.stdo)
                                print('\n-- stderr --\n')
                                print(res.stde)
                            return 1
        return 0

def filter_tests(suite, tests):
    if suite is None:
        return tests
    return [x for x in tests if suite in x.suite]


def run(args):
    options = parser.parse_args(args)
    if options.benchmark:
        options.num_processes = 1

    if options.gdb:
        options.verbose = True

    options.wd = os.path.abspath(options.wd)

    th = TestHarness(options)
    if options.list:
        return th.run_special()
    if not options.no_rebuild:
        if not th.rebuild_all():
            sys.exit(-1)
    if len(options.args) == 0:
        return th.doit()
    return th.run_special()

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
