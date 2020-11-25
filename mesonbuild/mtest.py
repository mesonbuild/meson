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
from collections import deque, namedtuple
from copy import deepcopy
import argparse
import asyncio
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
from .coredata import major_versions_differ, MesonVersionMismatchException
from .coredata import version as coredata_version
from .dependencies import ExternalProgram
from .mesonlib import MesonException, OrderedSet, get_wine_shortpath, split_args, join_args
from .mintro import get_infodir, load_info_file
from .backend.backends import TestProtocol, TestSerialisation

# GNU autotools interprets a return code of 77 from tests it executes to
# mean that the test should be skipped.
GNU_SKIP_RETURNCODE = 77

# GNU autotools interprets a return code of 99 from tests it executes to
# mean that the test failed even before testing what it is supposed to test.
GNU_ERROR_RETURNCODE = 99

def is_windows() -> bool:
    platname = platform.system().lower()
    return platname == 'windows'

def is_cygwin() -> bool:
    return sys.platform == 'cygwin'

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
                        help='Optional list of test names to run. "testname" to run all tests with that name, '
                        '"subprojname:testname" to specifically run "testname" from "subprojname", '
                        '"subprojname:" to run all tests defined by "subprojname".')


def print_safe(s: str) -> None:
    try:
        print(s)
    except UnicodeEncodeError:
        s = s.encode('ascii', errors='backslashreplace').decode('ascii')
        print(s)

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

    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    OK = 'OK'
    TIMEOUT = 'TIMEOUT'
    INTERRUPT = 'INTERRUPT'
    SKIP = 'SKIP'
    FAIL = 'FAIL'
    EXPECTEDFAIL = 'EXPECTEDFAIL'
    UNEXPECTEDPASS = 'UNEXPECTEDPASS'
    ERROR = 'ERROR'

    @staticmethod
    def maxlen() -> int:
        return 14 # len(UNEXPECTEDPASS)

    def is_ok(self) -> bool:
        return self in {TestResult.OK, TestResult.EXPECTEDFAIL}

    def is_bad(self) -> bool:
        return self in {TestResult.FAIL, TestResult.TIMEOUT, TestResult.INTERRUPT,
                        TestResult.UNEXPECTEDPASS, TestResult.ERROR}

    def get_text(self, colorize: bool) -> str:
        result_str = '{res:{reslen}}'.format(res=self.value, reslen=self.maxlen())
        if self.is_bad():
            decorator = mlog.red
        elif self in (TestResult.SKIP, TestResult.EXPECTEDFAIL):
            decorator = mlog.yellow
        else:
            decorator = mlog.green
        return decorator(result_str).get_text(colorize)


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
            if directive.startswith('SKIP'):
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


class TestLogger:
    def flush(self) -> None:
        pass

    def start(self, harness: 'TestHarness') -> None:
        pass

    def start_test(self, test: 'TestRun') -> None:
        pass

    def log(self, harness: 'TestHarness', result: 'TestRun') -> None:
        pass

    async def finish(self, harness: 'TestHarness') -> None:
        pass

    def close(self) -> None:
        pass


class TestFileLogger(TestLogger):
    def __init__(self, filename: str, errors: str = 'replace') -> None:
        self.filename = filename
        self.file = open(filename, 'w', encoding='utf8', errors=errors)

    def close(self) -> None:
        if self.file:
            self.file.close()
            self.file = None


class ConsoleLogger(TestLogger):
    SPINNER = "\U0001f311\U0001f312\U0001f313\U0001f314" + \
              "\U0001f315\U0001f316\U0001f317\U0001f318"

    def __init__(self) -> None:
        self.update = asyncio.Event()
        self.running_tests = OrderedSet()  # type: OrderedSet['TestRun']
        self.progress_test = None          # type: T.Optional['TestRun']
        self.progress_task = None          # type: T.Optional[asyncio.Future]
        self.stop = False
        self.update = asyncio.Event()
        self.should_erase_line = ''
        self.test_count = 0
        self.started_tests = 0
        self.spinner_index = 0

    def flush(self) -> None:
        if self.should_erase_line:
            print(self.should_erase_line, end='')
            self.should_erase_line = ''

    def print_progress(self, line: str) -> None:
        print(self.should_erase_line, line, sep='', end='\r')
        self.should_erase_line = '\x1b[K'

    def request_update(self) -> None:
        self.update.set()

    def emit_progress(self) -> None:
        if self.progress_test is None:
            self.flush()
            return

        if len(self.running_tests) == 1:
            count = '{}/{}'.format(self.started_tests, self.test_count)
        else:
            count = '{}-{}/{}'.format(self.started_tests - len(self.running_tests) + 1,
                                      self.started_tests, self.test_count)

        line = '[{}] {} {}'.format(count, self.SPINNER[self.spinner_index], self.progress_test.name)
        self.spinner_index = (self.spinner_index + 1) % len(self.SPINNER)
        self.print_progress(line)

    @staticmethod
    def is_tty() -> bool:
        try:
            _, _ = os.get_terminal_size(1)
            return True
        except OSError:
            return False

    def start(self, harness: 'TestHarness') -> None:
        async def report_progress() -> None:
            loop = asyncio.get_event_loop()
            next_update = 0.0
            self.request_update()
            while not self.stop:
                await self.update.wait()
                self.update.clear()

                # We may get here simply because the progress line has been
                # overwritten, so do not always switch.  Only do so every
                # second, or if the printed test has finished
                if loop.time() >= next_update:
                    self.progress_test = None
                    next_update = loop.time() + 1
                    loop.call_at(next_update, self.request_update)

                if (self.progress_test and
                        self.progress_test.res is not TestResult.RUNNING):
                    self.progress_test = None

                if not self.progress_test:
                    if not self.running_tests:
                        continue
                    # Pick a test in round robin order
                    self.progress_test = self.running_tests.pop(last=False)
                    self.running_tests.add(self.progress_test)

                self.emit_progress()
            self.flush()

        self.test_count = harness.test_count
        # In verbose mode, the progress report gets in the way of the tests'
        # stdout and stderr.
        if self.is_tty() and not harness.options.verbose:
            self.progress_task = asyncio.ensure_future(report_progress())

    def start_test(self, test: 'TestRun') -> None:
        self.started_tests += 1
        self.running_tests.add(test)
        self.running_tests.move_to_end(test, last=False)
        self.request_update()

    def log(self, harness: 'TestHarness', result: 'TestRun') -> None:
        self.running_tests.remove(result)
        if not harness.options.quiet or not result.res.is_ok():
            self.flush()
            print(harness.format(result, mlog.colorize_console()), flush=True)
        self.request_update()

    async def finish(self, harness: 'TestHarness') -> None:
        self.stop = True
        self.request_update()
        if self.progress_task:
            await self.progress_task

        if harness.collected_failures:
            if harness.options.print_errorlogs:
                if len(harness.collected_failures) > 10:
                    print('\n\nThe output from 10 first failed tests:\n')
                else:
                    print('\n\nThe output from the failed tests:\n')
                for i, result in enumerate(harness.collected_failures, 1):
                    print(harness.format(result, mlog.colorize_console()))
                    print_safe(result.get_log_short())
                    if i == 10:
                        break

            print("\nSummary of Failures:\n")
            for i, result in enumerate(harness.collected_failures, 1):
                print(harness.format(result, mlog.colorize_console()))

        print(harness.summary())


class TextLogfileBuilder(TestFileLogger):
    def start(self, harness: 'TestHarness') -> None:
        self.file.write('Log of Meson test suite run on {}\n\n'.format(datetime.datetime.now().isoformat()))
        inherit_env = env_tuple_to_str(os.environ.items())
        self.file.write('Inherited environment: {}\n\n'.format(inherit_env))

    def log(self, harness: 'TestHarness', result: 'TestRun') -> None:
        self.file.write(harness.format(result, False))
        self.file.write("\n\n" + result.get_log() + "\n")

    async def finish(self, harness: 'TestHarness') -> None:
        if harness.collected_failures:
            self.file.write("\nSummary of Failures:\n\n")
            for i, result in enumerate(harness.collected_failures, 1):
                self.file.write(harness.format(result, False) + '\n')
        self.file.write(harness.summary())

        print('Full log written to {}'.format(self.filename))


class JsonLogfileBuilder(TestFileLogger):
    def log(self, harness: 'TestHarness', result: 'TestRun') -> None:
        jresult = {'name': result.name,
                   'stdout': result.stdo,
                   'result': result.res.value,
                   'starttime': result.starttime,
                   'duration': result.duration,
                   'returncode': result.returncode,
                   'env': result.env,
                   'command': result.cmd}  # type: T.Dict[str, T.Any]
        if result.stde:
            jresult['stderr'] = result.stde
        self.file.write(json.dumps(jresult) + '\n')


class JunitBuilder(TestLogger):

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

    def log(self, harness: 'TestHarness', test: 'TestRun') -> None:
        """Log a single test case."""
        if test.junit is not None:
            for suite in test.junit.findall('.//testsuite'):
                # Assume that we don't need to merge anything here...
                suite.attrib['name'] = '{}.{}.{}'.format(test.project, test.name, suite.attrib['name'])

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
            suitename = '{}.{}'.format(test.project, test.name)
            assert suitename not in self.suites, 'duplicate suite'

            suite = self.suites[suitename] = et.Element(
                'testsuite',
                name=suitename,
                tests=str(len(test.results)),
                errors=str(sum(1 for r in test.results if r in
                               {TestResult.INTERRUPT, TestResult.ERROR})),
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
                elif result is TestResult.INTERRUPT:
                    fail = et.SubElement(testcase, 'failure')
                    fail.text = 'Test was interrupted by user.'
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

            testcase = et.SubElement(suite, 'testcase', name=test.name, classname=test.name)
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

    async def finish(self, harness: 'TestHarness') -> None:
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
    TEST_NUM = 0

    def __init__(self, test: TestSerialisation, test_env: T.Dict[str, str],
                 name: str):
        self.res = TestResult.PENDING
        self.test = test
        self._num = None       # type: T.Optional[int]
        self.name = name
        self.results = list()  # type: T.List[TestResult]
        self.returncode = 0
        self.starttime = None  # type: T.Optional[float]
        self.duration = None   # type: T.Optional[float]
        self.stdo = None       # type: T.Optional[str]
        self.stde = None       # type: T.Optional[str]
        self.cmd = None        # type: T.Optional[T.List[str]]
        self.env = dict()      # type: T.Dict[str, str]
        self.should_fail = test.should_fail
        self.project = test.project_name
        self.junit = None      # type: T.Optional[et.ElementTree]

    def start(self) -> None:
        self.res = TestResult.RUNNING
        self.starttime = time.time()

    def complete_gtest(self, returncode: int,
                       stdo: T.Optional[str], stde: T.Optional[str],
                       cmd: T.List[str]) -> None:
        filename = '{}.xml'.format(self.test.name)
        if self.test.workdir:
            filename = os.path.join(self.test.workdir, filename)
        tree = et.parse(filename)

        self.complete_exitcode(returncode, stdo, stde, cmd, junit=tree)

    def complete_exitcode(self, returncode: int,
                          stdo: T.Optional[str], stde: T.Optional[str],
                          cmd: T.List[str],
                          **kwargs: T.Any) -> None:
        if returncode == GNU_SKIP_RETURNCODE:
            res = TestResult.SKIP
        elif returncode == GNU_ERROR_RETURNCODE:
            res = TestResult.ERROR
        elif self.should_fail:
            res = TestResult.EXPECTEDFAIL if bool(returncode) else TestResult.UNEXPECTEDPASS
        else:
            res = TestResult.FAIL if bool(returncode) else TestResult.OK
        self.complete(res, [], returncode, stdo, stde, cmd, **kwargs)

    def complete_tap(self, returncode: int, stdo: str, stde: str, cmd: T.List[str]) -> None:
        res = None    # type: T.Optional[TestResult]
        results = []  # type: T.List[TestResult]
        failed = False

        for i in TAPParser(io.StringIO(stdo)).parse():
            if isinstance(i, TAPParser.Bailout):
                results.append(TestResult.ERROR)
                failed = True
            elif isinstance(i, TAPParser.Test):
                results.append(i.result)
                if i.result not in {TestResult.OK, TestResult.EXPECTEDFAIL, TestResult.SKIP}:
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
            elif self.should_fail:
                res = TestResult.EXPECTEDFAIL if failed else TestResult.UNEXPECTEDPASS
            else:
                res = TestResult.FAIL if failed else TestResult.OK

        self.complete(res, results, returncode, stdo, stde, cmd)

    @property
    def num(self) -> int:
        if self._num is None:
            TestRun.TEST_NUM += 1
            self._num = TestRun.TEST_NUM
        return self._num

    def complete(self, res: TestResult, results: T.List[TestResult],
                 returncode: int,
                 stdo: T.Optional[str], stde: T.Optional[str],
                 cmd: T.List[str], *, junit: T.Optional[et.ElementTree] = None) -> None:
        assert isinstance(res, TestResult)
        self.res = res
        self.results = results
        self.returncode = returncode
        self.duration = time.time() - self.starttime
        self.stdo = stdo
        self.stde = stde
        self.cmd = cmd
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
        res += '-------\n'
        return res

    def get_log_short(self) -> str:
        log = self.get_log()
        lines = log.splitlines()
        if len(lines) < 103:
            return log
        else:
            log = '\n'.join(lines[:2])
            log += '\n--- Listing only the last 100 lines from a long log. ---\n'
            log += lines[2] + '\n'
            log += '\n'.join(lines[-100:])
            return log

def decode(stream: T.Union[None, bytes]) -> str:
    if stream is None:
        return ''
    try:
        return stream.decode('utf-8')
    except UnicodeDecodeError:
        return stream.decode('iso-8859-1', errors='ignore')

def run_with_mono(fname: str) -> bool:
    return fname.endswith('.exe') and not (is_windows() or is_cygwin())

def check_testdata(objs: T.List[TestSerialisation]) -> T.List[TestSerialisation]:
    if not isinstance(objs, list):
        raise MesonVersionMismatchException('<unknown>', coredata_version)
    for obj in objs:
        if not isinstance(obj, TestSerialisation):
            raise MesonVersionMismatchException('<unknown>', coredata_version)
        if not hasattr(obj, 'version'):
            raise MesonVersionMismatchException('<unknown>', coredata_version)
        if major_versions_differ(obj.version, coredata_version):
            raise MesonVersionMismatchException(obj.version, coredata_version)
    return objs

def load_benchmarks(build_dir: str) -> T.List[TestSerialisation]:
    datafile = Path(build_dir) / 'meson-private' / 'meson_benchmark_setup.dat'
    if not datafile.is_file():
        raise TestException('Directory {!r} does not seem to be a Meson build directory.'.format(build_dir))
    with datafile.open('rb') as f:
        objs = check_testdata(pickle.load(f))
    return objs

def load_tests(build_dir: str) -> T.List[TestSerialisation]:
    datafile = Path(build_dir) / 'meson-private' / 'meson_test_setup.dat'
    if not datafile.is_file():
        raise TestException('Directory {!r} does not seem to be a Meson build directory.'.format(build_dir))
    with datafile.open('rb') as f:
        objs = check_testdata(pickle.load(f))
    return objs

# Custom waiting primitives for asyncio

async def try_wait_one(*awaitables: T.Any, timeout: T.Optional[T.Union[int, float]]) -> None:
    try:
        await asyncio.wait(awaitables,
                           timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
    except asyncio.TimeoutError:
        pass

async def complete(future: asyncio.Future) -> None:
    """Wait for completion of the given future, ignoring cancellation."""
    try:
        await future
    except asyncio.CancelledError:
        pass

async def complete_all(futures: T.Iterable[asyncio.Future]) -> None:
    """Wait for completion of all the given futures, ignoring cancellation."""
    while futures:
        done, futures = await asyncio.wait(futures, return_when=asyncio.FIRST_EXCEPTION)
        # Raise exceptions if needed for all the "done" futures
        for f in done:
            if not f.cancelled():
                f.result()


class SingleTestRunner:

    def __init__(self, test: TestSerialisation, test_env: T.Dict[str, str],
                 env: T.Dict[str, str], name: str,
                 options: argparse.Namespace):
        self.test = test
        self.test_env = test_env
        self.env = env
        self.options = options
        self.runobj = TestRun(test, test_env, name)

    def _get_cmd(self) -> T.Optional[T.List[str]]:
        if self.test.fname[0].endswith('.jar'):
            return ['java', '-jar'] + self.test.fname
        elif not self.test.is_cross_built and run_with_mono(self.test.fname[0]):
            return ['mono'] + self.test.fname
        elif self.test.cmd_is_built and self.test.is_cross_built and self.test.needs_exe_wrapper:
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

    async def run(self) -> TestRun:
        cmd = self._get_cmd()
        self.runobj.start()
        if cmd is None:
            skip_stdout = 'Not run because can not execute cross compiled binaries.'
            self.runobj.complete(TestResult.SKIP, [], GNU_SKIP_RETURNCODE, skip_stdout, None, None)
        else:
            wrap = TestHarness.get_wrapper(self.options)
            if self.options.gdb:
                self.test.timeout = None
            await self._run_cmd(wrap + cmd + self.test.cmd_args + self.options.test_args)
        return self.runobj

    async def _run_subprocess(self, args: T.List[str], *, timeout: T.Optional[int],
                              stdout: T.IO, stderr: T.IO,
                              env: T.Dict[str, str], cwd: T.Optional[str]) -> T.Tuple[int, TestResult, T.Optional[str]]:
        async def kill_process(p: asyncio.subprocess.Process) -> T.Optional[str]:
            # Python does not provide multiplatform support for
            # killing a process and all its children so we need
            # to roll our own.
            try:
                if is_windows():
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(p.pid)])
                else:
                    # Send a termination signal to the process group that setsid()
                    # created - giving it a chance to perform any cleanup.
                    os.killpg(p.pid, signal.SIGTERM)

                    # Make sure the termination signal actually kills the process
                    # group, otherwise retry with a SIGKILL.
                    await try_wait_one(p.wait(), timeout=0.5)
                    if p.returncode is not None:
                        return None

                    os.killpg(p.pid, signal.SIGKILL)

                await try_wait_one(p.wait(), timeout=1)
                if p.returncode is not None:
                    return None

                # An earlier kill attempt has not worked for whatever reason.
                # Try to kill it one last time with a direct call.
                # If the process has spawned children, they will remain around.
                p.kill()
                await try_wait_one(p.wait(), timeout=1)
                if p.returncode is not None:
                    return None
                return 'Test process could not be killed.'
            except ProcessLookupError:
                # Sometimes (e.g. with Wine) this happens.  There's nothing
                # we can do, probably the process already died so just wait
                # for the event loop to pick that up.
                await p.wait()
                return None

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
                os.setsid()

        p = await asyncio.create_subprocess_exec(*args,
                                                 stdout=stdout,
                                                 stderr=stderr,
                                                 env=env,
                                                 cwd=cwd,
                                                 preexec_fn=preexec_fn if not is_windows() else None)
        result = None
        additional_error = None
        try:
            await try_wait_one(p.wait(), timeout=timeout)
            if p.returncode is None:
                if self.options.verbose:
                    print('{} time out (After {} seconds)'.format(self.test.name, timeout))
                additional_error = await kill_process(p)
                result = TestResult.TIMEOUT
        except asyncio.CancelledError:
            # The main loop must have seen Ctrl-C.
            additional_error = await kill_process(p)
            result = TestResult.INTERRUPT
        finally:
            if self.options.gdb:
                # Let us accept ^C again
                signal.signal(signal.SIGINT, previous_sigint_handler)

        return p.returncode or 0, result, additional_error

    async def _run_cmd(self, cmd: T.List[str]) -> None:
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

        extra_cmd = []  # type: T.List[str]
        if self.test.protocol is TestProtocol.GTEST:
            gtestname = self.test.name
            if self.test.workdir:
                gtestname = os.path.join(self.test.workdir, self.test.name)
            extra_cmd.append('--gtest_output=xml:{}.xml'.format(gtestname))

        if self.test.timeout is None:
            timeout = None
        elif self.options.timeout_multiplier is not None:
            timeout = self.test.timeout * self.options.timeout_multiplier
        else:
            timeout = self.test.timeout

        returncode, result, additional_error = await self._run_subprocess(cmd + extra_cmd,
                                                                          timeout=timeout,
                                                                          stdout=stdout,
                                                                          stderr=stderr,
                                                                          env=self.env,
                                                                          cwd=self.test.workdir)
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
        if result:
            self.runobj.complete(result, [], returncode, stdo, stde, cmd)
        else:
            if self.test.protocol is TestProtocol.EXITCODE:
                self.runobj.complete_exitcode(returncode, stdo, stde, cmd)
            elif self.test.protocol is TestProtocol.GTEST:
                self.runobj.complete_gtest(returncode, stdo, stde, cmd)
            else:
                if self.options.verbose:
                    print(stdo, end='')
                self.runobj.complete_tap(returncode, stdo, stde, cmd)

class TestHarness:
    def __init__(self, options: argparse.Namespace):
        self.options = options
        self.collected_failures = []  # type: T.List[TestRun]
        self.fail_count = 0
        self.expectedfail_count = 0
        self.unexpectedpass_count = 0
        self.success_count = 0
        self.skip_count = 0
        self.timeout_count = 0
        self.test_count = 0
        self.name_max_len = 0
        self.is_run = False
        self.loggers = []         # type: T.List[TestLogger]
        self.loggers.append(ConsoleLogger())

        if self.options.benchmark:
            self.tests = load_benchmarks(options.wd)
        else:
            self.tests = load_tests(options.wd)
        ss = set()
        for t in self.tests:
            for s in t.suite:
                ss.add(s)
        self.suites = list(ss)

    def __enter__(self) -> 'TestHarness':
        return self

    def __exit__(self, exc_type: T.Any, exc_value: T.Any, traceback: T.Any) -> None:
        self.close_logfiles()

    def close_logfiles(self) -> None:
        for l in self.loggers:
            l.close()

    def merge_suite_options(self, options: argparse.Namespace, test: TestSerialisation) -> T.Dict[str, str]:
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

    def get_test_runner(self, test: TestSerialisation, name: str) -> SingleTestRunner:
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
        return SingleTestRunner(test, test_env, env, name, options)

    def process_test_result(self, result: TestRun) -> None:
        if result.res is TestResult.TIMEOUT:
            self.timeout_count += 1
        elif result.res is TestResult.SKIP:
            self.skip_count += 1
        elif result.res is TestResult.OK:
            self.success_count += 1
        elif result.res in {TestResult.FAIL, TestResult.ERROR, TestResult.INTERRUPT}:
            self.fail_count += 1
        elif result.res is TestResult.EXPECTEDFAIL:
            self.expectedfail_count += 1
        elif result.res is TestResult.UNEXPECTEDPASS:
            self.unexpectedpass_count += 1
        else:
            sys.exit('Unknown test result encountered: {}'.format(result.res))

        if result.res.is_bad():
            self.collected_failures.append(result)
        for l in self.loggers:
            l.log(self, result)

    def format(self, result: TestRun, colorize: bool) -> str:
        result_str = '{num:{numlen}}/{testcount} {name:{name_max_len}} {res} {dur:.2f}s'.format(
            numlen=len(str(self.test_count)),
            num=result.num,
            testcount=self.test_count,
            name_max_len=self.name_max_len,
            name=result.name,
            res=result.res.get_text(colorize),
            dur=result.duration)
        if result.res is TestResult.FAIL:
            result_str += ' ' + returncode_to_status(result.returncode)
        return result_str

    def summary(self) -> str:
        return textwrap.dedent('''

            Ok:                 {:<4}
            Expected Fail:      {:<4}
            Fail:               {:<4}
            Unexpected Pass:    {:<4}
            Skipped:            {:<4}
            Timeout:            {:<4}
            ''').format(self.success_count, self.expectedfail_count, self.fail_count,
                        self.unexpectedpass_count, self.skip_count, self.timeout_count)

    def total_failure_count(self) -> int:
        return self.fail_count + self.unexpectedpass_count + self.timeout_count

    def doit(self, options: argparse.Namespace) -> int:
        if self.is_run:
            raise RuntimeError('Test harness object can only be used once.')
        self.is_run = True
        tests = self.get_tests()
        if not tests:
            return 0
        if not options.no_rebuild and not rebuild_deps(options.wd, tests):
            # We return 125 here in case the build failed.
            # The reason is that exit code 125 tells `git bisect run` that the current
            # commit should be skipped.  Thus users can directly use `meson test` to
            # bisect without needing to handle the does-not-build case separately in a
            # wrapper script.
            sys.exit(125)

        self.test_count = len(tests)
        self.name_max_len = max([len(self.get_pretty_suite(test)) for test in tests])
        self.run_tests(tests)
        return self.total_failure_count()

    @staticmethod
    def split_suite_string(suite: str) -> T.Tuple[str, str]:
        if ':' in suite:
            split = suite.split(':', 1)
            assert len(split) == 2
            return split[0], split[1]
        else:
            return suite, ""

    @staticmethod
    def test_in_suites(test: TestSerialisation, suites: T.List[str]) -> bool:
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

    def test_suitable(self, test: TestSerialisation) -> bool:
        return ((not self.options.include_suites or
                TestHarness.test_in_suites(test, self.options.include_suites)) and not
                TestHarness.test_in_suites(test, self.options.exclude_suites))

    def tests_from_args(self, tests: T.List[TestSerialisation]) -> T.Generator[TestSerialisation, None, None]:
        '''
        Allow specifying test names like "meson test foo1 foo2", where test('foo1', ...)

        Also support specifying the subproject to run tests from like
        "meson test subproj:" (all tests inside subproj) or "meson test subproj:foo1"
        to run foo1 inside subproj. Coincidentally also "meson test :foo1" to
        run all tests with that name across all subprojects, which is
        identical to "meson test foo1"
        '''
        for arg in self.options.args:
            if ':' in arg:
                subproj, name = arg.split(':', maxsplit=1)
            else:
                subproj, name = '', arg
            for t in tests:
                if subproj and t.project_name != subproj:
                    continue
                if name and t.name != name:
                    continue
                yield t

    def get_tests(self) -> T.List[TestSerialisation]:
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

        if self.options.args:
            tests = list(self.tests_from_args(tests))

        if not tests:
            print('No suitable tests defined.')
            return []

        return tests

    def flush_logfiles(self) -> None:
        for l in self.loggers:
            l.flush()

    def open_logfiles(self) -> None:
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

        self.loggers.append(JunitBuilder(logfile_base + '.junit.xml'))
        self.loggers.append(JsonLogfileBuilder(logfile_base + '.json'))
        self.loggers.append(TextLogfileBuilder(logfile_base + '.txt', errors='surrogateescape'))

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

    def get_pretty_suite(self, test: TestSerialisation) -> str:
        if len(self.suites) > 1 and test.suite:
            rv = TestHarness.split_suite_string(test.suite[0])[0]
            s = "+".join(TestHarness.split_suite_string(s)[1] for s in test.suite)
            if s:
                rv += ":"
            return rv + s + " / " + test.name
        else:
            return test.name

    def run_tests(self, tests: T.List[TestSerialisation]) -> None:
        try:
            self.open_logfiles()
            # Replace with asyncio.run once we can require Python 3.7
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._run_tests(tests))
        finally:
            self.close_logfiles()

    async def _run_tests(self, tests: T.List[TestSerialisation]) -> None:
        semaphore = asyncio.Semaphore(self.options.num_processes)
        futures = deque()  # type: T.Deque[asyncio.Future]
        running_tests = dict() # type: T.Dict[asyncio.Future, str]
        startdir = os.getcwd()
        if self.options.wd:
            os.chdir(self.options.wd)
        self.build_data = build.load(os.getcwd())
        interrupted = False

        async def run_test(test: SingleTestRunner) -> None:
            async with semaphore:
                if interrupted or (self.options.repeat > 1 and self.fail_count):
                    return
                for l in self.loggers:
                    l.start_test(test.runobj)
                res = await test.run()
                self.process_test_result(res)

        def test_done(f: asyncio.Future) -> None:
            if not f.cancelled():
                f.result()
            futures.remove(f)
            try:
                del running_tests[f]
            except KeyError:
                pass

        def cancel_one_test(warn: bool) -> None:
            future = futures.popleft()
            futures.append(future)
            if warn:
                self.flush_logfiles()
                mlog.warning('CTRL-C detected, interrupting {}'.format(running_tests[future]))
            del running_tests[future]
            future.cancel()

        def sigterm_handler() -> None:
            nonlocal interrupted
            if interrupted:
                return
            interrupted = True
            self.flush_logfiles()
            mlog.warning('Received SIGTERM, exiting')
            while running_tests:
                cancel_one_test(False)

        def sigint_handler() -> None:
            # We always pick the longest-running future that has not been cancelled
            # If all the tests have been CTRL-C'ed, just stop
            nonlocal interrupted
            if interrupted:
                return
            if running_tests:
                cancel_one_test(True)
            else:
                self.flush_logfiles()
                mlog.warning('CTRL-C detected, exiting')
                interrupted = True

        for l in self.loggers:
            l.start(self)

        if sys.platform != 'win32':
            asyncio.get_event_loop().add_signal_handler(signal.SIGINT, sigint_handler)
            asyncio.get_event_loop().add_signal_handler(signal.SIGTERM, sigterm_handler)
        try:
            for _ in range(self.options.repeat):
                for test in tests:
                    visible_name = self.get_pretty_suite(test)
                    single_test = self.get_test_runner(test, visible_name)

                    if not test.is_parallel or single_test.options.gdb:
                        await complete_all(futures)
                    future = asyncio.ensure_future(run_test(single_test))
                    futures.append(future)
                    running_tests[future] = visible_name
                    future.add_done_callback(test_done)
                    if not test.is_parallel or single_test.options.gdb:
                        await complete(future)
                if self.options.repeat > 1 and self.fail_count:
                    break

            await complete_all(futures)
        finally:
            if sys.platform != 'win32':
                asyncio.get_event_loop().remove_signal_handler(signal.SIGINT)
                asyncio.get_event_loop().remove_signal_handler(signal.SIGTERM)
            for l in self.loggers:
                await l.finish(self)
            os.chdir(startdir)

def list_tests(th: TestHarness) -> bool:
    tests = th.get_tests()
    for t in tests:
        print(th.get_pretty_suite(t))
    return not tests

def rebuild_deps(wd: str, tests: T.List[TestSerialisation]) -> bool:
    if not (Path(wd) / 'build.ninja').is_file():
        print('Only ninja backend is supported to rebuild tests before running them.')
        return True

    ninja = environment.detect_ninja()
    if not ninja:
        print("Can't find ninja, can't rebuild test.")
        return False

    depends = set()            # type: T.Set[str]
    targets = set()            # type: T.Set[str]
    intro_targets = dict()     # type: T.Dict[str, T.List[str]]
    for target in load_info_file(get_infodir(wd), kind='targets'):
        intro_targets[target['id']] = [
                os.path.relpath(f, wd)
                for f in target['filename']]
    for t in tests:
        for d in t.depends:
            if d in depends:
                continue
            depends.update(d)
            targets.update(intro_targets[d])

    ret = subprocess.run(ninja + ['-C', wd] + sorted(targets)).returncode
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

    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)

    if check_bin is not None:
        exe = ExternalProgram(check_bin, silent=True)
        if not exe.found():
            print('Could not find requested program: {!r}'.format(check_bin))
            return 1

    with TestHarness(options) as th:
        try:
            if options.list:
                return list_tests(th)
            return th.doit(options)
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
