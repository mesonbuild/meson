# Copyright 2016-2017 The Meson development team

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
from mesonbuild.mesonlib import substring_is_in_list, MesonException
from mesonbuild import mlog

import time, datetime, multiprocessing, json
import concurrent.futures as conc
import platform
import signal
import random
from copy import deepcopy
import enum

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

def buildparser():
    parser = argparse.ArgumentParser(prog='meson test')
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
    return parser


def returncode_to_status(retcode):
    # Note: We can't use `os.WIFSIGNALED(result.returncode)` and the related
    # functions here because the status returned by subprocess is munged. It
    # returns a negative value if the process was killed by a signal rather than
    # the raw status returned by `wait()`. Also, If a shell sits between Meson
    # the the actual unit test that shell is likely to convert a termination due
    # to a signal into an exit status of 128 plus the signal number.
    if retcode < 0:
        signum = -retcode
        try:
            signame = signal.Signals(signum).name
        except ValueError:
            signame = 'SIGinvalid'
        return '(killed by signal %d %s)' % (signum, signame)

    if retcode <= 128:
        return '(exit status %d)' % (retcode,)

    signum = retcode - 128
    try:
        signame = signal.Signals(signum).name
    except ValueError:
        signame = 'SIGinvalid'
    return '(exit status %d or signal %d %s)' % (retcode, signum, signame)

def env_tuple_to_str(env):
    return ''.join(["%s='%s' " % (k, v) for k, v in env])


class TestException(MesonException):
    pass


@enum.unique
class TestResult(enum.Enum):

    OK = 'OK'
    TIMEOUT = 'TIMEOUT'
    SKIP = 'SKIP'
    FAIL = 'FAIL'


class TestRun:
    def __init__(self, res, returncode, should_fail, duration, stdo, stde, cmd,
                 env):
        assert isinstance(res, TestResult)
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
            test_only_env = set(self.env.items()) - set(os.environ.items())
            res += '{}{}\n'.format(env_tuple_to_str(test_only_env), ' '.join(self.cmd))
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
               'result': result.res.value,
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

def load_benchmarks(build_dir):
    datafile = os.path.join(build_dir, 'meson-private', 'meson_benchmark_setup.dat')
    if not os.path.isfile(datafile):
        raise TestException('Directory ${!r} does not seem to be a Meson build directory.'.format(build_dir))
    with open(datafile, 'rb') as f:
        obj = pickle.load(f)
    return obj

def load_tests(build_dir):
    datafile = os.path.join(build_dir, 'meson-private', 'meson_test_setup.dat')
    if not os.path.isfile(datafile):
        raise TestException('Directory ${!r} does not seem to be a Meson build directory.'.format(build_dir))
    with open(datafile, 'rb') as f:
        obj = pickle.load(f)
    return obj


class SingleTestRunner:

    def __init__(self, test, env, options):
        self.test = test
        self.env = env
        self.options = options

    def _get_cmd(self):
        if self.test.fname[0].endswith('.jar'):
            return ['java', '-jar'] + self.test.fname
        elif not self.test.is_cross_built and run_with_mono(self.test.fname[0]):
            return ['mono'] + self.test.fname
        else:
            if self.test.is_cross_built:
                if self.test.exe_runner is None:
                    # Can not run test on cross compiled executable
                    # because there is no execute wrapper.
                    return None
                else:
                    if not self.test.exe_runner.found():
                        msg = 'The exe_wrapper defined in the cross file {!r} was not ' \
                              'found. Please check the command and/or add it to PATH.'
                        raise TestException(msg.format(self.test.exe_runner.name))
                    return self.test.exe_runner.get_command() + self.test.fname
            else:
                return self.test.fname

    def run(self):
        cmd = self._get_cmd()
        if cmd is None:
            skip_stdout = 'Not run because can not execute cross compiled binaries.'
            return TestRun(res=TestResult.SKIP, returncode=GNU_SKIP_RETURNCODE,
                           should_fail=self.test.should_fail, duration=0.0,
                           stdo=skip_stdout, stde=None, cmd=None, env=self.test.env)
        else:
            wrap = TestHarness.get_wrapper(self.options)
            if self.options.gdb:
                self.test.timeout = None
            return self._run_cmd(wrap + cmd + self.test.cmd_args + self.options.test_args)

    def _run_cmd(self, cmd):
        starttime = time.time()

        if len(self.test.extra_paths) > 0:
            self.env['PATH'] = os.pathsep.join(self.test.extra_paths + ['']) + self.env['PATH']
            if substring_is_in_list('wine', cmd):
                wine_paths = ['Z:' + p for p in self.test.extra_paths]
                wine_path = ';'.join(wine_paths)
                # Don't accidentally end with an `;` because that will add the
                # current directory and might cause unexpected behaviour
                if 'WINEPATH' in self.env:
                    self.env['WINEPATH'] = wine_path + ';' + self.env['WINEPATH']
                else:
                    self.env['WINEPATH'] = wine_path

        # If MALLOC_PERTURB_ is not set, or if it is set to an empty value,
        # (i.e., the test or the environment don't explicitly set it), set
        # it ourselves. We do this unconditionally for regular tests
        # because it is extremely useful to have.
        # Setting MALLOC_PERTURB_="0" will completely disable this feature.
        if ('MALLOC_PERTURB_' not in self.env or not self.env['MALLOC_PERTURB_']) and not self.options.benchmark:
            self.env['MALLOC_PERTURB_'] = str(random.randint(1, 255))

        stdout = None
        stderr = None
        if not self.options.verbose:
            stdout = subprocess.PIPE
            stderr = subprocess.PIPE if self.options and self.options.split else subprocess.STDOUT

        # Let gdb handle ^C instead of us
        if self.options.gdb:
            previous_sigint_handler = signal.getsignal(signal.SIGINT)
            # Make the meson executable ignore SIGINT while gdb is running.
            signal.signal(signal.SIGINT, signal.SIG_IGN)

        def preexec_fn():
            if self.options.gdb:
                # Restore the SIGINT handler for the child process to
                # ensure it can handle it.
                signal.signal(signal.SIGINT, signal.SIG_DFL)
            else:
                # We don't want setsid() in gdb because gdb needs the
                # terminal in order to handle ^C and not show tcsetpgrp()
                # errors avoid not being able to use the terminal.
                os.setsid()

        p = subprocess.Popen(cmd,
                             stdout=stdout,
                             stderr=stderr,
                             env=self.env,
                             cwd=self.test.workdir,
                             preexec_fn=preexec_fn if not is_windows() else None)
        timed_out = False
        kill_test = False
        if self.test.timeout is None:
            timeout = None
        elif self.options.timeout_multiplier is not None:
            timeout = self.test.timeout * self.options.timeout_multiplier
        else:
            timeout = self.test.timeout
        try:
            (stdo, stde) = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if self.options.verbose:
                print('%s time out (After %d seconds)' % (self.test.name, timeout))
            timed_out = True
        except KeyboardInterrupt:
            mlog.warning('CTRL-C detected while running %s' % (self.test.name))
            kill_test = True
        finally:
            if self.options.gdb:
                # Let us accept ^C again
                signal.signal(signal.SIGINT, previous_sigint_handler)

        if kill_test or timed_out:
            # Python does not provide multiplatform support for
            # killing a process and all its children so we need
            # to roll our own.
            if is_windows():
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(p.pid)])
            else:
                try:
                    # Kill the process group that setsid() created.
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    # Sometimes (e.g. with Wine) this happens.
                    # There's nothing we can do (maybe the process
                    # already died) so carry on.
                    pass
            try:
                (stdo, stde) = p.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                # An earlier kill attempt has not worked for whatever reason.
                # Try to kill it one last time with a direct call.
                # If the process has spawned children, they will remain around.
                p.kill()
                try:
                    (stdo, stde) = p.communicate(timeout=1)
                except subprocess.TimeoutExpired:
                    stdo = b'Test process could not be killed.'
                    stde = b''
            except ValueError:
                stdo = b'Could not read output. Maybe the process has redirected its stdout/stderr?'
                stde = b''
        endtime = time.time()
        duration = endtime - starttime
        stdo = decode(stdo)
        if stde:
            stde = decode(stde)
        if timed_out:
            res = TestResult.TIMEOUT
        elif p.returncode == GNU_SKIP_RETURNCODE:
            res = TestResult.SKIP
        elif self.test.should_fail == bool(p.returncode):
            res = TestResult.OK
        else:
            res = TestResult.FAIL
        return TestRun(res, p.returncode, self.test.should_fail, duration, stdo, stde, cmd, self.test.env)


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
        self.logfilename = None
        self.logfile = None
        self.jsonlogfile = None
        if self.options.benchmark:
            self.tests = load_benchmarks(options.wd)
        else:
            self.tests = load_tests(options.wd)
        self.load_suites()

    def __del__(self):
        if self.logfile:
            self.logfile.close()
        if self.jsonlogfile:
            self.jsonlogfile.close()

    def merge_suite_options(self, options, test):
        if ':' in options.setup:
            if options.setup not in self.build_data.test_setups:
                sys.exit("Unknown test setup '%s'." % options.setup)
            current = self.build_data.test_setups[options.setup]
        else:
            full_name = test.project_name + ":" + options.setup
            if full_name not in self.build_data.test_setups:
                sys.exit("Test setup '%s' not found from project '%s'." % (options.setup, test.project_name))
            current = self.build_data.test_setups[full_name]
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
        return current.env.get_env(os.environ.copy())

    def get_test_runner(self, test):
        options = deepcopy(self.options)
        if options.setup:
            env = self.merge_suite_options(options, test)
        else:
            env = os.environ.copy()
        if isinstance(test.env, build.EnvironmentVariables):
            test.env = test.env.get_env(env)
        env.update(test.env)
        return SingleTestRunner(test, env, options)

    def process_test_result(self, result):
        if result.res is TestResult.TIMEOUT:
            self.timeout_count += 1
            self.fail_count += 1
        elif result.res is TestResult.SKIP:
            self.skip_count += 1
        elif result.res is TestResult.OK:
            self.success_count += 1
        elif result.res is TestResult.FAIL:
            self.fail_count += 1
        else:
            sys.exit('Unknown test result encountered: {}'.format(result.res))

    def print_stats(self, numlen, tests, name, result, i):
        startpad = ' ' * (numlen - len('%d' % (i + 1)))
        num = '%s%d/%d' % (startpad, i + 1, len(tests))
        padding1 = ' ' * (38 - len(name))
        padding2 = ' ' * (8 - len(result.res.value))
        status = ''

        if result.res is TestResult.FAIL:
            status = returncode_to_status(result.returncode)
        result_str = '%s %s  %s%s%s%5.2f s %s' % \
            (num, name, padding1, result.res.value, padding2, result.duration,
             status)
        if not self.options.quiet or result.res is not TestResult.OK:
            if result.res is not TestResult.OK and mlog.colorize_console:
                if result.res in (TestResult.FAIL, TestResult.TIMEOUT):
                    decorator = mlog.red
                elif result.res is TestResult.SKIP:
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
        if self.logfile:
            self.logfile.write(result_str)
        if self.jsonlogfile:
            write_json_log(self.jsonlogfile, name, result)

    def print_summary(self):
        msg = '''
OK:      %4d
FAIL:    %4d
SKIP:    %4d
TIMEOUT: %4d
''' % (self.success_count, self.fail_count, self.skip_count, self.timeout_count)
        print(msg)
        if self.logfile:
            self.logfile.write(msg)

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

                # the SUITE can be passed as
                #     suite_name
                # or
                #     project_name:suite_name
                # so we need to select only the test belonging to project_name

                # this if hanlde the first case (i.e., SUITE == suite_name)

                # in this way we can run tests belonging to different
                # (sub)projects which share the same suite_name
                if not st_match and st == prj_match:
                    return True

                # these two conditions are needed to handle the second option
                # i.e., SUITE == project_name:suite_name

                # in this way we select the only the tests of
                # project_name with suite_name
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
            namebase = os.path.basename(self.get_wrapper(self.options)[0])
        elif self.options.setup:
            namebase = self.options.setup.replace(":", "_")

        if namebase:
            logfile_base += '-' + namebase.replace(' ', '_')
        self.logfilename = logfile_base + '.txt'
        self.jsonlogfilename = logfile_base + '.json'

        self.jsonlogfile = open(self.jsonlogfilename, 'w', encoding='utf-8')
        self.logfile = open(self.logfilename, 'w', encoding='utf-8')

        self.logfile.write('Log of Meson test suite run on %s\n\n'
                           % datetime.datetime.now().isoformat())
        inherit_env = env_tuple_to_str(os.environ.items())
        self.logfile.write('Inherited environment: {}\n\n'.format(inherit_env))

    @staticmethod
    def get_wrapper(options):
        wrap = []
        if options.gdb:
            wrap = ['gdb', '--quiet', '--nh']
            if options.repeat > 1:
                wrap += ['-ex', 'run', '-ex', 'quit']
            # Signal the end of arguments to gdb
            wrap += ['--args']
        if options.wrapper:
            wrap += options.wrapper
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
        futures = []
        numlen = len('%d' % len(tests))
        self.open_log_files()
        startdir = os.getcwd()
        if self.options.wd:
            os.chdir(self.options.wd)
        self.build_data = build.load(os.getcwd())

        try:
            for _ in range(self.options.repeat):
                for i, test in enumerate(tests):
                    visible_name = self.get_pretty_suite(test)

                    if not test.is_parallel or self.options.gdb:
                        self.drain_futures(futures)
                        futures = []
                        single_test = self.get_test_runner(test)
                        res = single_test.run()
                        self.process_test_result(res)
                        self.print_stats(numlen, tests, visible_name, res, i)
                    else:
                        if not executor:
                            executor = conc.ThreadPoolExecutor(max_workers=self.options.num_processes)
                        single_test = self.get_test_runner(test)
                        f = executor.submit(single_test.run)
                        futures.append((f, numlen, tests, visible_name, i))
                    if self.options.repeat > 1 and self.fail_count:
                        break
                if self.options.repeat > 1 and self.fail_count:
                    break

            self.drain_futures(futures)
            self.print_summary()
            self.print_collected_logs()

            if self.logfilename:
                print('Full log written to %s' % self.logfilename)
        finally:
            os.chdir(startdir)

    def drain_futures(self, futures):
        for i in futures:
            (result, numlen, tests, name, i) = i
            if self.options.repeat > 1 and self.fail_count:
                result.cancel()
            if self.options.verbose:
                result.result()
            self.process_test_result(result.result())
            self.print_stats(numlen, tests, name, result.result(), i)

    def run_special(self):
        '''Tests run by the user, usually something like "under gdb 1000 times".'''
        if self.is_run:
            raise RuntimeError('Can not use run_special after a full run.')
        tests = self.get_tests()
        if not tests:
            return 0
        self.run_tests(tests)
        return self.fail_count


def list_tests(th):
    tests = th.get_tests()
    for t in tests:
        print(th.get_pretty_suite(t))

def rebuild_all(wd):
    if not os.path.isfile(os.path.join(wd, 'build.ninja')):
        print('Only ninja backend is supported to rebuild tests before running them.')
        return True

    ninja = environment.detect_ninja()
    if not ninja:
        print("Can't find ninja, can't rebuild test.")
        return False

    p = subprocess.Popen([ninja, '-C', wd])
    p.communicate()

    if p.returncode != 0:
        print('Could not rebuild')
        return False

    return True

def run(args):
    options = buildparser().parse_args(args)

    if options.benchmark:
        options.num_processes = 1

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
            print('Could not find requested program: {!r}'.format(check_bin))
            return 1
    options.wd = os.path.abspath(options.wd)

    if not options.list and not options.no_rebuild:
        if not rebuild_all(options.wd):
            return 1

    try:
        th = TestHarness(options)
        if options.list:
            list_tests(th)
            return 0
        if not options.args:
            return th.doit()
        return th.run_special()
    except TestException as e:
        print('Meson test encountered an error:\n')
        if os.environ.get('MESON_FORCE_BACKTRACE'):
            raise e
        else:
            print(e)
        return 1
