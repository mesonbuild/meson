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

from pathlib import Path
from collections import namedtuple
from copy import deepcopy
import argparse
import concurrent.futures as conc
import datetime
import enum
import io
import json
import multiprocessing
import os
import pickle
import platform
import random
import re
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import typing as T
import xml.etree.ElementTree as et

from . import build
from . import environment
from . import mlog
from .dependencies import ExternalProgram
from .mesonlib import MesonException, get_wine_shortpath, split_args, join_args
from .backend.backends import TestProtocol

if T.TYPE_CHECKING:
    from .backend.backends import TestSerialisation

# GNU autotools interprets a return code of 77 from tests it executes to
# mean that the test should be skipped.
GNU_SKIP_RETURNCODE = 77

# GNU autotools interprets a return code of 99 from tests it executes to
# mean that the test failed even before testing what it is supposed to test.
GNU_ERROR_RETURNCODE = 99

def is_windows() -> bool:
    platname = platform.system().lower()
    return platname == 'windows' or 'mingw' in platname

def is_cygwin() -> bool:
    platname = platform.system().lower()
    return 'cygwin' in platname

def determine_worker_count() -> int:
    varname = 'MESON_TESTTHREADS'
    if varname in os.environ:
        try:
            num_workers = int(os.environ[varname])
        except ValueError:
            print('Invalid value in {}, using 1 thread.'.format(varname))
            num_workers = 1
    else:
        try:
            # Fails in some weird environments such as Debian
            # reproducible build.
            num_workers = multiprocessing.cpu_count()
        except Exception:
            num_workers = 1
    return num_workers

def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--repeat', default=1, dest='repeat', type=int,
                        help='Number of times to run the tests.')
    parser.add_argument('--no-rebuild', default=False, action='store_true',
                        help='Do not rebuild before running tests.')
    parser.add_argument('--gdb', default=False, dest='gdb', action='store_true',
                        help='Run test under gdb.')
    parser.add_argument('--gdb-path', default='gdb', dest='gdb_path',
                        help='Path to the gdb binary (default: gdb).')
    parser.add_argument('--list', default=False, dest='list', action='store_true',
                        help='List available tests.')
    parser.add_argument('--wrapper', default=None, dest='wrapper', type=split_args,
                        help='wrapper to run tests with (e.g. Valgrind)')
    parser.add_argument('-C', default='.', dest='wd',
                        # https://github.com/python/typeshed/issues/3107
                        # https://github.com/python/mypy/issues/7177
                        type=os.path.abspath,  # type: ignore
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
    parser.add_argument('--test-args', default=[], type=split_args,
                        help='Arguments to pass to the specified test(s) or all tests')
    parser.add_argument('args', nargs='*',
                        help='Optional list of tests to run')


def returncode_to_status(retcode: int) -> str:
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
        return '(killed by signal {} {})'.format(signum, signame)

    if retcode <= 128:
        return '(exit status {})'.format(retcode)

    signum = retcode - 128
    try:
        signame = signal.Signals(signum).name
    except ValueError:
        signame = 'SIGinvalid'
    return '(exit status {} or signal {} {})'.format(retcode, signum, signame)

def env_tuple_to_str(env: T.Iterable[T.Tuple[str, str]]) -> str:
    return ''.join(["{}='{}' ".format(k, v) for k, v in env])


class TestException(MesonException):
    pass


@enum.unique
class TestResult(enum.Enum):

    OK = 'OK'
    TIMEOUT = 'TIMEOUT'
    SKIP = 'SKIP'
    FAIL = 'FAIL'
    EXPECTEDFAIL = 'EXPECTEDFAIL'
    UNEXPECTEDPASS = 'UNEXPECTEDPASS'
    ERROR = 'ERROR'

    @staticmethod
    def maxlen() -> int:
        return 14 # len(UNEXPECTEDPASS)


class TAPParser:
    Plan = namedtuple('Plan', ['count', 'late', 'skipped', 'explanation'])
    Bailout = namedtuple('Bailout', ['message'])
    Test = namedtuple('Test', ['number', 'name', 'result', 'explanation'])
    Error = namedtuple('Error', ['message'])
    Version = namedtuple('Version', ['version'])

    _MAIN = 1
    _AFTER_TEST = 2
    _YAML = 3

    _RE_BAILOUT = re.compile(r'Bail out!\s*(.*)')
    _RE_DIRECTIVE = re.compile(r'(?:\s*\#\s*([Ss][Kk][Ii][Pp]\S*|[Tt][Oo][Dd][Oo])\b\s*(.*))?')
    _RE_PLAN = re.compile(r'1\.\.([0-9]+)' + _RE_DIRECTIVE.pattern)
    _RE_TEST = re.compile(r'((?:not )?ok)\s*(?:([0-9]+)\s*)?([^#]*)' + _RE_DIRECTIVE.pattern)
    _RE_VERSION = re.compile(r'TAP version ([0-9]+)')
    _RE_YAML_START = re.compile(r'(\s+)---.*')
    _RE_YAML_END = re.compile(r'\s+\.\.\.\s*')

    def __init__(self, io: T.Iterator[str]):
        self.io = io

    def parse_test(self, ok: bool, num: int, name: str, directive: T.Optional[str], explanation: T.Optional[str]) -> \
            T.Generator[T.Union['TAPParser.Test', 'TAPParser.Error'], None, None]:
        name = name.strip()
        explanation = explanation.strip() if explanation else None
        if directive is not None:
            directive = directive.upper()
            if directive == 'SKIP':
                if ok:
                    yield self.Test(num, name, TestResult.SKIP, explanation)
                    return
            elif directive == 'TODO':
                yield self.Test(num, name, TestResult.UNEXPECTEDPASS if ok else TestResult.EXPECTEDFAIL, explanation)
                return
            else:
                yield self.Error('invalid directive "{}"'.format(directive,))

        yield self.Test(num, name, TestResult.OK if ok else TestResult.FAIL, explanation)

    def parse(self) -> T.Generator[T.Union['TAPParser.Test', 'TAPParser.Error', 'TAPParser.Version', 'TAPParser.Plan', 'TAPParser.Bailout'], None, None]:
        found_late_test = False
        bailed_out = False
        plan = None
        lineno = 0
        num_tests = 0
        yaml_lineno = None
        yaml_indent = ''
        state = self._MAIN
        version = 12
        while True:
            lineno += 1
            try:
                line = next(self.io).rstrip()
            except StopIteration:
                break

            # YAML blocks are only accepted after a test
            if state == self._AFTER_TEST:
                if version >= 13:
                    m = self._RE_YAML_START.match(line)
                    if m:
                        state = self._YAML
                        yaml_lineno = lineno
                        yaml_indent = m.group(1)
                        continue
                state = self._MAIN

            elif state == self._YAML:
                if self._RE_YAML_END.match(line):
                    state = self._MAIN
                    continue
                if line.startswith(yaml_indent):
                    continue
                yield self.Error('YAML block not terminated (started on line {})'.format(yaml_lineno))
                state = self._MAIN

            assert state == self._MAIN
            if line.startswith('#'):
                continue

            m = self._RE_TEST.match(line)
            if m:
                if plan and plan.late and not found_late_test:
                    yield self.Error('unexpected test after late plan')
                    found_late_test = True
                num_tests += 1
                num = num_tests if m.group(2) is None else int(m.group(2))
                if num != num_tests:
                    yield self.Error('out of order test numbers')
                yield from self.parse_test(m.group(1) == 'ok', num,
                                           m.group(3), m.group(4), m.group(5))
                state = self._AFTER_TEST
                continue

            m = self._RE_PLAN.match(line)
            if m:
                if plan:
                    yield self.Error('more than one plan found')
                else:
                    count = int(m.group(1))
                    skipped = (count == 0)
                    if m.group(2):
                        if m.group(2).upper().startswith('SKIP'):
                            if count > 0:
                                yield self.Error('invalid SKIP directive for plan')
                            skipped = True
                        else:
                            yield self.Error('invalid directive for plan')
                    plan = self.Plan(count=count, late=(num_tests > 0),
                                     skipped=skipped, explanation=m.group(3))
                    yield plan
                continue

            m = self._RE_BAILOUT.match(line)
            if m:
                yield self.Bailout(m.group(1))
                bailed_out = True
                continue

            m = self._RE_VERSION.match(line)
            if m:
                # The TAP version is only accepted as the first line
                if lineno != 1:
                    yield self.Error('version number must be on the first line')
                    continue
                version = int(m.group(1))
                if version < 13:
                    yield self.Error('version number should be at least 13')
                else:
                    yield self.Version(version=version)
                continue

            if not line:
                continue

            yield self.Error('unexpected input at line {}'.format((lineno,)))

        if state == self._YAML:
            yield self.Error('YAML block not terminated (started on line {})'.format(yaml_lineno))

        if not bailed_out and plan and num_tests != plan.count:
            if num_tests < plan.count:
                yield self.Error('Too few tests run (expected {}, got {})'.format(plan.count, num_tests))
            else:
                yield self.Error('Too many tests run (expected {}, got {})'.format(plan.count, num_tests))



class JunitBuilder:

    """Builder for Junit test results.

    Junit is impossible to stream out, it requires attributes counting the
    total number of tests, failures, skips, and errors in the root element
    and in each test suite. As such, we use a builder class to track each
    test case, and calculate all metadata before writing it out.

    For tests with multiple results (like from a TAP test), we record the
    test as a suite with the project_name.test_name. This allows us to track
    each result separately. For tests with only one result (such as exit-code
    tests) we record each one into a suite with the name project_name. The use
    of the project_name allows us to sort subproject tests separately from
    the root project.
    """

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.root = et.Element(
            'testsuites', tests='0', errors='0', failures='0')
        self.suites = {}  # type: T.Dict[str, et.Element]

    def log(self, name: str, test: 'TestRun') -> None:
        """Log a single test case."""
        if test.junit is not None:
            for suite in test.junit.findall('.//testsuite'):
                # Assume that we don't need to merge anything here...
                suite.attrib['name'] = '{}.{}.{}'.format(test.project, name, suite.attrib['name'])

                # GTest can inject invalid attributes
                for case in suite.findall('.//testcase[@result]'):
                    del case.attrib['result']
                for case in suite.findall('.//testcase[@timestamp]'):
                    del case.attrib['timestamp']
                self.root.append(suite)
            return

        # In this case we have a test binary with multiple results.
        # We want to record this so that each result is recorded
        # separately
        if test.results:
            suitename = '{}.{}'.format(test.project, name)
            assert suitename not in self.suites, 'duplicate suite'

            suite = self.suites[suitename] = et.Element(
                'testsuite',
                name=suitename,
                tests=str(len(test.results)),
                errors=str(sum(1 for r in test.results if r is TestResult.ERROR)),
                failures=str(sum(1 for r in test.results if r in
                                 {TestResult.FAIL, TestResult.UNEXPECTEDPASS, TestResult.TIMEOUT})),
                skipped=str(sum(1 for r in test.results if r is TestResult.SKIP)),
            )

            for i, result in enumerate(test.results):
                # Both name and classname are required. Set them both to the
                # number of the test in a TAP test, as TAP doesn't give names.
                testcase = et.SubElement(suite, 'testcase', name=str(i), classname=str(i))
                if result is TestResult.SKIP:
                    et.SubElement(testcase, 'skipped')
                elif result is TestResult.ERROR:
                    et.SubElement(testcase, 'error')
                elif result is TestResult.FAIL:
                    et.SubElement(testcase, 'failure')
                elif result is TestResult.UNEXPECTEDPASS:
                    fail = et.SubElement(testcase, 'failure')
                    fail.text = 'Test unexpected passed.'
                elif result is TestResult.TIMEOUT:
                    fail = et.SubElement(testcase, 'failure')
                    fail.text = 'Test did not finish before configured timeout.'
            if test.stdo:
                out = et.SubElement(suite, 'system-out')
                out.text = test.stdo.rstrip()
            if test.stde:
                err = et.SubElement(suite, 'system-err')
                err.text = test.stde.rstrip()
        else:
            if test.project not in self.suites:
                suite = self.suites[test.project] = et.Element(
                    'testsuite', name=test.project, tests='1', errors='0',
                    failures='0', skipped='0')
            else:
                suite = self.suites[test.project]
                suite.attrib['tests'] = str(int(suite.attrib['tests']) + 1)

            testcase = et.SubElement(suite, 'testcase', name=name, classname=name)
            if test.res is TestResult.SKIP:
                et.SubElement(testcase, 'skipped')
                suite.attrib['skipped'] = str(int(suite.attrib['skipped']) + 1)
            elif test.res is TestResult.ERROR:
                et.SubElement(testcase, 'error')
                suite.attrib['errors'] = str(int(suite.attrib['errors']) + 1)
            elif test.res is TestResult.FAIL:
                et.SubElement(testcase, 'failure')
                suite.attrib['failures'] = str(int(suite.attrib['failures']) + 1)
            if test.stdo:
                out = et.SubElement(testcase, 'system-out')
                out.text = test.stdo.rstrip()
            if test.stde:
                err = et.SubElement(testcase, 'system-err')
                err.text = test.stde.rstrip()

    def write(self) -> None:
        """Calculate total test counts and write out the xml result."""
        for suite in self.suites.values():
            self.root.append(suite)
            # Skipped is really not allowed in the "testsuits" element
            for attr in ['tests', 'errors', 'failures']:
                self.root.attrib[attr] = str(int(self.root.attrib[attr]) + int(suite.attrib[attr]))

        tree = et.ElementTree(self.root)
        with open(self.filename, 'wb') as f:
            tree.write(f, encoding='utf-8', xml_declaration=True)


class TestRun:

    @classmethod
    def make_gtest(cls, test: 'TestSerialisation', test_env: T.Dict[str, str],
                   returncode: int, starttime: float, duration: float,
                   stdo: T.Optional[str], stde: T.Optional[str],
                   cmd: T.Optional[T.List[str]]) -> 'TestRun':
        filename = '{}.xml'.format(test.name)
        if test.workdir:
            filename = os.path.join(test.workdir, filename)
        tree = et.parse(filename)

        return cls.make_exitcode(
            test, test_env, returncode, starttime, duration, stdo, stde, cmd,
            junit=tree)

    @classmethod
    def make_exitcode(cls, test: 'TestSerialisation', test_env: T.Dict[str, str],
                      returncode: int, starttime: float, duration: float,
                      stdo: T.Optional[str], stde: T.Optional[str],
                      cmd: T.Optional[T.List[str]], **kwargs) -> 'TestRun':
        if returncode == GNU_SKIP_RETURNCODE:
            res = TestResult.SKIP
        elif returncode == GNU_ERROR_RETURNCODE:
            res = TestResult.ERROR
        elif test.should_fail:
            res = TestResult.EXPECTEDFAIL if bool(returncode) else TestResult.UNEXPECTEDPASS
        else:
            res = TestResult.FAIL if bool(returncode) else TestResult.OK
        return cls(test, test_env, res, [], returncode, starttime, duration, stdo, stde, cmd, **kwargs)

    @classmethod
    def make_tap(cls, test: 'TestSerialisation', test_env: T.Dict[str, str],
                 returncode: int, starttime: float, duration: float,
                 stdo: str, stde: str,
                 cmd: T.Optional[T.List[str]]) -> 'TestRun':
        res = None    # type: T.Optional[TestResult]
        results = []  # type: T.List[TestResult]
        failed = False

        for i in TAPParser(io.StringIO(stdo)).parse():
            if isinstance(i, TAPParser.Bailout):
                results.append(TestResult.ERROR)
                failed = True
            elif isinstance(i, TAPParser.Test):
                results.append(i.result)
                if i.result not in {TestResult.OK, TestResult.EXPECTEDFAIL}:
                    failed = True
            elif isinstance(i, TAPParser.Error):
                results.append(TestResult.ERROR)
                stde += '\nTAP parsing error: ' + i.message
                failed = True

        if returncode != 0:
            res = TestResult.ERROR
            stde += '\n(test program exited with status code {})'.format(returncode,)

        if res is None:
            # Now determine the overall result of the test based on the outcome of the subcases
            if all(t is TestResult.SKIP for t in results):
                # This includes the case where num_tests is zero
                res = TestResult.SKIP
            elif test.should_fail:
                res = TestResult.EXPECTEDFAIL if failed else TestResult.UNEXPECTEDPASS
            else:
                res = TestResult.FAIL if failed else TestResult.OK

        return cls(test, test_env, res, results, returncode, starttime, duration, stdo, stde, cmd)

    def __init__(self, test: 'TestSerialisation', test_env: T.Dict[str, str],
                 res: TestResult, results: T.List[TestResult], returncode:
                 int, starttime: float, duration: float,
                 stdo: T.Optional[str], stde: T.Optional[str],
                 cmd: T.Optional[T.List[str]], *, junit: T.Optional[et.ElementTree] = None):
        assert isinstance(res, TestResult)
        self.res = res
        self.results = results  # May be an empty list
        self.returncode = returncode
        self.starttime = starttime
        self.duration = duration
        self.stdo = stdo
        self.stde = stde
        self.cmd = cmd
        self.env = test_env
        self.should_fail = test.should_fail
        self.project = test.project_name
        self.junit = junit

    def get_log(self) -> str:
        res = '--- command ---\n'
        if self.cmd is None:
            res += 'NONE\n'
        else:
            test_only_env = set(self.env.items()) - set(os.environ.items())
            starttime_str = time.strftime("%H:%M:%S", time.gmtime(self.starttime))
            res += '{} {}{}\n'.format(
                starttime_str, env_tuple_to_str(test_only_env), ' '.join(self.cmd)
            )
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

def decode(stream: T.Union[None, bytes]) -> str:
    if stream is None:
        return ''
    try:
        return stream.decode('utf-8')
    except UnicodeDecodeError:
        return stream.decode('iso-8859-1', errors='ignore')

def write_json_log(jsonlogfile: T.TextIO, test_name: str, result: TestRun) -> None:
    jresult = {'name': test_name,
               'stdout': result.stdo,
               'result': result.res.value,
               'starttime': result.starttime,
               'duration': result.duration,
               'returncode': result.returncode,
               'env': result.env,
               'command': result.cmd}  # type: T.Dict[str, T.Any]
    if result.stde:
        jresult['stderr'] = result.stde
    jsonlogfile.write(json.dumps(jresult) + '\n')

def run_with_mono(fname: str) -> bool:
    return fname.endswith('.exe') and not (is_windows() or is_cygwin())

def load_benchmarks(build_dir: str) -> T.List['TestSerialisation']:
    datafile = Path(build_dir) / 'meson-private' / 'meson_benchmark_setup.dat'
    if not datafile.is_file():
        raise TestException('Directory {!r} does not seem to be a Meson build directory.'.format(build_dir))
    with datafile.open('rb') as f:
        obj = T.cast(T.List['TestSerialisation'], pickle.load(f))
    return obj

def load_tests(build_dir: str) -> T.List['TestSerialisation']:
    datafile = Path(build_dir) / 'meson-private' / 'meson_test_setup.dat'
    if not datafile.is_file():
        raise TestException('Directory {!r} does not seem to be a Meson build directory.'.format(build_dir))
    with datafile.open('rb') as f:
        obj = T.cast(T.List['TestSerialisation'], pickle.load(f))
    return obj


class SingleTestRunner:

    def __init__(self, test: 'TestSerialisation', test_env: T.Dict[str, str],
                 env: T.Dict[str, str], options: argparse.Namespace):
        self.test = test
        self.test_env = test_env
        self.env = env
        self.options = options

    def _get_cmd(self) -> T.Optional[T.List[str]]:
        if self.test.fname[0].endswith('.jar'):
            return ['java', '-jar'] + self.test.fname
        elif not self.test.is_cross_built and run_with_mono(self.test.fname[0]):
            return ['mono'] + self.test.fname
        elif self.test.cmd_is_built and self.test.needs_exe_wrapper:
            if self.test.exe_runner is None:
                # Can not run test on cross compiled executable
                # because there is no execute wrapper.
                return None
            elif self.test.cmd_is_built:
                # If the command is not built (ie, its a python script),
                # then we don't check for the exe-wrapper
                if not self.test.exe_runner.found():
                    msg = ('The exe_wrapper defined in the cross file {!r} was not '
                           'found. Please check the command and/or add it to PATH.')
                    raise TestException(msg.format(self.test.exe_runner.name))
                return self.test.exe_runner.get_command() + self.test.fname
        return self.test.fname

    def run(self) -> TestRun:
        cmd = self._get_cmd()
        if cmd is None:
            skip_stdout = 'Not run because can not execute cross compiled binaries.'
            return TestRun(self.test, self.test_env, TestResult.SKIP, [], GNU_SKIP_RETURNCODE, time.time(), 0.0, skip_stdout, None, None)
        else:
            wrap = TestHarness.get_wrapper(self.options)
            if self.options.gdb:
                self.test.timeout = None
            return self._run_cmd(wrap + cmd + self.test.cmd_args + self.options.test_args)

    def _run_cmd(self, cmd: T.List[str]) -> TestRun:
        starttime = time.time()

        if self.test.extra_paths:
            self.env['PATH'] = os.pathsep.join(self.test.extra_paths + ['']) + self.env['PATH']
            winecmd = []
            for c in cmd:
                winecmd.append(c)
                if os.path.basename(c).startswith('wine'):
                    self.env['WINEPATH'] = get_wine_shortpath(
                        winecmd,
                        ['Z:' + p for p in self.test.extra_paths] + self.env.get('WINEPATH', '').split(';')
                    )
                    break

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
            stdout = tempfile.TemporaryFile("wb+")
            stderr = tempfile.TemporaryFile("wb+") if self.options.split else stdout
        if self.test.protocol is TestProtocol.TAP and stderr is stdout:
            stdout = tempfile.TemporaryFile("wb+")

        # Let gdb handle ^C instead of us
        if self.options.gdb:
            previous_sigint_handler = signal.getsignal(signal.SIGINT)
            # Make the meson executable ignore SIGINT while gdb is running.
            signal.signal(signal.SIGINT, signal.SIG_IGN)

        def preexec_fn() -> None:
            if self.options.gdb:
                # Restore the SIGINT handler for the child process to
                # ensure it can handle it.
                signal.signal(signal.SIGINT, signal.SIG_DFL)
            else:
                # We don't want setsid() in gdb because gdb needs the
                # terminal in order to handle ^C and not show tcsetpgrp()
                # errors avoid not being able to use the terminal.
                os.setsid()  # type: ignore

        extra_cmd = []  # type: T.List[str]
        if self.test.protocol is TestProtocol.GTEST:
            gtestname = '{}.xml'.format(self.test.name)
            if self.test.workdir:
                gtestname = '{}:{}'.format(self.test.workdir, self.test.name)
            extra_cmd.append('--gtest_output=xml:{}'.format(gtestname))

        p = subprocess.Popen(cmd + extra_cmd,
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
            p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if self.options.verbose:
                print('{} time out (After {} seconds)'.format(self.test.name, timeout))
            timed_out = True
        except KeyboardInterrupt:
            mlog.warning('CTRL-C detected while running {}'.format(self.test.name))
            kill_test = True
        finally:
            if self.options.gdb:
                # Let us accept ^C again
                signal.signal(signal.SIGINT, previous_sigint_handler)

        additional_error = None

        if kill_test or timed_out:
            # Python does not provide multiplatform support for
            # killing a process and all its children so we need
            # to roll our own.
            if is_windows():
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(p.pid)])
            else:

                def _send_signal_to_process_group(pgid : int, signum : int):
                    """ sends a signal to a process group """
                    try:
                        os.killpg(pgid, signum) # type: ignore
                    except ProcessLookupError:
                        # Sometimes (e.g. with Wine) this happens.
                        # There's nothing we can do (maybe the process
                        # already died) so carry on.
                        pass

                # Send a termination signal to the process group that setsid()
                # created - giving it a chance to perform any cleanup.
                _send_signal_to_process_group(p.pid, signal.SIGTERM)

                # Make sure the termination signal actually kills the process
                # group, otherwise retry with a SIGKILL.
                try:
                    p.communicate(timeout=0.5)
                except subprocess.TimeoutExpired:
                    _send_signal_to_process_group(p.pid, signal.SIGKILL)
            try:
                p.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                # An earlier kill attempt has not worked for whatever reason.
                # Try to kill it one last time with a direct call.
                # If the process has spawned children, they will remain around.
                p.kill()
                try:
                    p.communicate(timeout=1)
                except subprocess.TimeoutExpired:
                    additional_error = 'Test process could not be killed.'
            except ValueError:
                additional_error = 'Could not read output. Maybe the process has redirected its stdout/stderr?'
        endtime = time.time()
        duration = endtime - starttime
        if additional_error is None:
            if stdout is None:
                stdo = ''
            else:
                stdout.seek(0)
                stdo = decode(stdout.read())
            if stderr is None or stderr is stdout:
                stde = ''
            else:
                stderr.seek(0)
                stde = decode(stderr.read())
        else:
            stdo = ""
            stde = additional_error
        if timed_out:
            return TestRun(self.test, self.test_env, TestResult.TIMEOUT, [], p.returncode, starttime, duration, stdo, stde, cmd)
        else:
            if self.test.protocol is TestProtocol.EXITCODE:
                return TestRun.make_exitcode(self.test, self.test_env, p.returncode, starttime, duration, stdo, stde, cmd)
            elif self.test.protocol is TestProtocol.GTEST:
                return TestRun.make_gtest(self.test, self.test_env, p.returncode, starttime, duration, stdo, stde, cmd)
            else:
                if self.options.verbose:
                    print(stdo, end='')
                return TestRun.make_tap(self.test, self.test_env, p.returncode, starttime, duration, stdo, stde, cmd)


class TestHarness:
    def __init__(self, options: argparse.Namespace):
        self.options = options
        self.collected_logs = []  # type: T.List[str]
        self.fail_count = 0
        self.expectedfail_count = 0
        self.unexpectedpass_count = 0
        self.success_count = 0
        self.skip_count = 0
        self.timeout_count = 0
        self.is_run = False
        self.tests = None
        self.results = []         # type: T.List[TestRun]
        self.logfilename = None   # type: T.Optional[str]
        self.logfile = None       # type: T.Optional[T.TextIO]
        self.jsonlogfile = None   # type: T.Optional[T.TextIO]
        self.junit = None         # type: T.Optional[JunitBuilder]
        if self.options.benchmark:
            self.tests = load_benchmarks(options.wd)
        else:
            self.tests = load_tests(options.wd)
        ss = set()
        for t in self.tests:
            for s in t.suite:
                ss.add(s)
        self.suites = list(ss)

    def __del__(self) -> None:
        self.close_logfiles()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close_logfiles()

    def close_logfiles(self) -> None:
        for f in ['logfile', 'jsonlogfile']:
            lfile =  getattr(self, f)
            if lfile:
                lfile.close()
                setattr(self, f, None)

    def merge_suite_options(self, options: argparse.Namespace, test: 'TestSerialisation') -> T.Dict[str, str]:
        if ':' in options.setup:
            if options.setup not in self.build_data.test_setups:
                sys.exit("Unknown test setup '{}'.".format(options.setup))
            current = self.build_data.test_setups[options.setup]
        else:
            full_name = test.project_name + ":" + options.setup
            if full_name not in self.build_data.test_setups:
                sys.exit("Test setup '{}' not found from project '{}'.".format(options.setup, test.project_name))
            current = self.build_data.test_setups[full_name]
        if not options.gdb:
            options.gdb = current.gdb
        if options.gdb:
            options.verbose = True
        if options.timeout_multiplier is None:
            options.timeout_multiplier = current.timeout_multiplier
    #    if options.env is None:
    #        options.env = current.env # FIXME, should probably merge options here.
        if options.wrapper is not None and current.exe_wrapper is not None:
            sys.exit('Conflict: both test setup and command line specify an exe wrapper.')
        if options.wrapper is None:
            options.wrapper = current.exe_wrapper
        return current.env.get_env(os.environ.copy())

    def get_test_runner(self, test: 'TestSerialisation') -> SingleTestRunner:
        options = deepcopy(self.options)
        if not options.setup:
            options.setup = self.build_data.test_setup_default_name
        if options.setup:
            env = self.merge_suite_options(options, test)
        else:
            env = os.environ.copy()
        test_env = test.env.get_env(env)
        env.update(test_env)
        if (test.is_cross_built and test.needs_exe_wrapper and
                test.exe_runner and test.exe_runner.found()):
            env['MESON_EXE_WRAPPER'] = join_args(test.exe_runner.get_command())
        return SingleTestRunner(test, test_env, env, options)

    def process_test_result(self, result: TestRun) -> None:
        if result.res is TestResult.TIMEOUT:
            self.timeout_count += 1
        elif result.res is TestResult.SKIP:
            self.skip_count += 1
        elif result.res is TestResult.OK:
            self.success_count += 1
        elif result.res is TestResult.FAIL or result.res is TestResult.ERROR:
            self.fail_count += 1
        elif result.res is TestResult.EXPECTEDFAIL:
            self.expectedfail_count += 1
        elif result.res is TestResult.UNEXPECTEDPASS:
            self.unexpectedpass_count += 1
        else:
            sys.exit('Unknown test result encountered: {}'.format(result.res))

    def print_stats(self, test_count: int, name_max_len: int,
                    tests: T.List['TestSerialisation'],
                    name: str, result: TestRun, i: int) -> None:
        ok_statuses = (TestResult.OK, TestResult.EXPECTEDFAIL)
        bad_statuses = (TestResult.FAIL, TestResult.TIMEOUT,
                        TestResult.UNEXPECTEDPASS, TestResult.ERROR)
        result_str = '{num:{numlen}}/{testcount} {name:{name_max_len}} {res:{reslen}} {dur:.2f}s'.format(
            numlen=len(str(test_count)),
            num=i,
            testcount=test_count,
            name_max_len=name_max_len,
            name=name,
            reslen=TestResult.maxlen(),
            res=result.res.value,
            dur=result.duration)
        if result.res is TestResult.FAIL:
            result_str += ' ' + returncode_to_status(result.returncode)
        if not self.options.quiet or result.res not in ok_statuses:
            if result.res not in ok_statuses and mlog.colorize_console:
                if result.res in bad_statuses:
                    decorator = mlog.red
                elif result.res is TestResult.SKIP:
                    decorator = mlog.yellow
                else:
                    sys.exit('Unreachable code was ... well ... reached.')
                print(decorator(result_str).get_text(True))
            else:
                print(result_str)
        result_str += "\n\n" + result.get_log()
        if result.res in bad_statuses:
            if self.options.print_errorlogs:
                self.collected_logs.append(result_str)
        if self.logfile:
            self.logfile.write(result_str)
        if self.jsonlogfile:
            write_json_log(self.jsonlogfile, name, result)
        if self.junit:
            self.junit.log(name, result)

    def print_summary(self) -> None:
        msg = textwrap.dedent('''
            Ok:                 {:<4}
            Expected Fail:      {:<4}
            Fail:               {:<4}
            Unexpected Pass:    {:<4}
            Skipped:            {:<4}
            Timeout:            {:<4}
            ''').format(self.success_count, self.expectedfail_count, self.fail_count,
           self.unexpectedpass_count, self.skip_count, self.timeout_count)
        print(msg)
        if self.logfile:
            self.logfile.write(msg)
        if self.junit:
            self.junit.write()

    def print_collected_logs(self) -> None:
        if self.collected_logs:
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
                    try:
                        print(line)
                    except UnicodeEncodeError:
                        line = line.encode('ascii', errors='replace').decode()
                        print(line)

    def total_failure_count(self) -> int:
        return self.fail_count + self.unexpectedpass_count + self.timeout_count

    def doit(self) -> int:
        if self.is_run:
            raise RuntimeError('Test harness object can only be used once.')
        self.is_run = True
        tests = self.get_tests()
        if not tests:
            return 0
        self.run_tests(tests)
        return self.total_failure_count()

    @staticmethod
    def split_suite_string(suite: str) -> T.Tuple[str, str]:
        if ':' in suite:
            # mypy can't figure out that str.split(n, 1) will return a list of
            # length 2, so we have to help it.
            return T.cast(T.Tuple[str, str], tuple(suite.split(':', 1)))
        else:
            return suite, ""

    @staticmethod
    def test_in_suites(test: 'TestSerialisation', suites: T.List[str]) -> bool:
        for suite in suites:
            (prj_match, st_match) = TestHarness.split_suite_string(suite)
            for prjst in test.suite:
                (prj, st) = TestHarness.split_suite_string(prjst)

                # the SUITE can be passed as
                #     suite_name
                # or
                #     project_name:suite_name
                # so we need to select only the test belonging to project_name

                # this if handle the first case (i.e., SUITE == suite_name)

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

    def test_suitable(self, test: 'TestSerialisation') -> bool:
        return ((not self.options.include_suites or
                TestHarness.test_in_suites(test, self.options.include_suites)) and not
                TestHarness.test_in_suites(test, self.options.exclude_suites))

    def get_tests(self) -> T.List['TestSerialisation']:
        if not self.tests:
            print('No tests defined.')
            return []

        if self.options.include_suites or self.options.exclude_suites:
            tests = []
            for tst in self.tests:
                if self.test_suitable(tst):
                    tests.append(tst)
        else:
            tests = self.tests

        # allow specifying test names like "meson test foo1 foo2", where test('foo1', ...)
        if self.options.args:
            tests = [t for t in tests if t.name in self.options.args]

        if not tests:
            print('No suitable tests defined.')
            return []

        return tests

    def open_log_files(self) -> None:
        if not self.options.logbase or self.options.verbose:
            return

        namebase = None
        logfile_base = os.path.join(self.options.wd, 'meson-logs', self.options.logbase)

        if self.options.wrapper:
            namebase = os.path.basename(self.get_wrapper(self.options)[0])
        elif self.options.setup:
            namebase = self.options.setup.replace(":", "_")

        if namebase:
            logfile_base += '-' + namebase.replace(' ', '_')

        self.junit = JunitBuilder(logfile_base + '.junit.xml')

        self.logfilename = logfile_base + '.txt'
        self.jsonlogfilename = logfile_base + '.json'

        self.jsonlogfile = open(self.jsonlogfilename, 'w', encoding='utf-8', errors='replace')
        self.logfile = open(self.logfilename, 'w', encoding='utf-8', errors='surrogateescape')

        self.logfile.write('Log of Meson test suite run on {}\n\n'.format(datetime.datetime.now().isoformat()))
        inherit_env = env_tuple_to_str(os.environ.items())
        self.logfile.write('Inherited environment: {}\n\n'.format(inherit_env))

    @staticmethod
    def get_wrapper(options: argparse.Namespace) -> T.List[str]:
        wrap = []  # type: T.List[str]
        if options.gdb:
            wrap = [options.gdb_path, '--quiet', '--nh']
            if options.repeat > 1:
                wrap += ['-ex', 'run', '-ex', 'quit']
            # Signal the end of arguments to gdb
            wrap += ['--args']
        if options.wrapper:
            wrap += options.wrapper
        return wrap

    def get_pretty_suite(self, test: 'TestSerialisation') -> str:
        if len(self.suites) > 1 and test.suite:
            rv = TestHarness.split_suite_string(test.suite[0])[0]
            s = "+".join(TestHarness.split_suite_string(s)[1] for s in test.suite)
            if s:
                rv += ":"
            return rv + s + " / " + test.name
        else:
            return test.name

    def run_tests(self, tests: T.List['TestSerialisation']) -> None:
        executor = None
        futures = []  # type: T.List[T.Tuple[conc.Future[TestRun], int, int, T.List[TestSerialisation], str, int]]
        test_count = len(tests)
        name_max_len = max([len(self.get_pretty_suite(test)) for test in tests])
        self.open_log_files()
        startdir = os.getcwd()
        if self.options.wd:
            os.chdir(self.options.wd)
        self.build_data = build.load(os.getcwd())

        try:
            for _ in range(self.options.repeat):
                for i, test in enumerate(tests, 1):
                    visible_name = self.get_pretty_suite(test)
                    single_test = self.get_test_runner(test)

                    if not test.is_parallel or self.options.num_processes == 1 or single_test.options.gdb:
                        self.drain_futures(futures)
                        futures = []
                        res = single_test.run()
                        self.process_test_result(res)
                        self.print_stats(test_count, name_max_len, tests, visible_name, res, i)
                    else:
                        if not executor:
                            executor = conc.ThreadPoolExecutor(max_workers=self.options.num_processes)
                        f = executor.submit(single_test.run)
                        futures.append((f, test_count, name_max_len, tests, visible_name, i))
                    if self.options.repeat > 1 and self.fail_count:
                        break
                if self.options.repeat > 1 and self.fail_count:
                    break

            self.drain_futures(futures)
            self.print_summary()
            self.print_collected_logs()

            if self.logfilename:
                print('Full log written to {}'.format(self.logfilename))
        finally:
            os.chdir(startdir)

    def drain_futures(self, futures: T.List[T.Tuple['conc.Future[TestRun]', int, int, T.List['TestSerialisation'], str, int]]) -> None:
        for x in futures:
            (result, test_count, name_max_len, tests, name, i) = x
            if self.options.repeat > 1 and self.fail_count:
                result.cancel()
            if self.options.verbose:
                result.result()
            self.process_test_result(result.result())
            self.print_stats(test_count, name_max_len, tests, name, result.result(), i)

    def run_special(self) -> int:
        '''Tests run by the user, usually something like "under gdb 1000 times".'''
        if self.is_run:
            raise RuntimeError('Can not use run_special after a full run.')
        tests = self.get_tests()
        if not tests:
            return 0
        self.run_tests(tests)
        return self.total_failure_count()


def list_tests(th: TestHarness) -> bool:
    tests = th.get_tests()
    for t in tests:
        print(th.get_pretty_suite(t))
    return not tests

def rebuild_all(wd: str) -> bool:
    if not (Path(wd) / 'build.ninja').is_file():
        print('Only ninja backend is supported to rebuild tests before running them.')
        return True

    ninja = environment.detect_ninja()
    if not ninja:
        print("Can't find ninja, can't rebuild test.")
        return False

    ret = subprocess.run([ninja, '-C', wd]).returncode
    if ret != 0:
        print('Could not rebuild {}'.format(wd))
        return False

    return True

def run(options: argparse.Namespace) -> int:
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

    if not options.list and not options.no_rebuild:
        if not rebuild_all(options.wd):
            # We return 125 here in case the build failed.
            # The reason is that exit code 125 tells `git bisect run` that the current commit should be skipped.
            # Thus users can directly use `meson test` to bisect without needing to handle the does-not-build case separately in a wrapper script.
            return 125

    with TestHarness(options) as th:
        try:
            if options.list:
                return list_tests(th)
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

def run_with_args(args: T.List[str]) -> int:
    parser = argparse.ArgumentParser(prog='meson test')
    add_arguments(parser)
    options = parser.parse_args(args)
    return run(options)
