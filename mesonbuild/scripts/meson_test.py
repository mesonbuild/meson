#!/usr/bin/env python3

# Copyright 2013-2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mesonbuild
import sys, os, subprocess, time, datetime, pickle, multiprocessing, json
import concurrent.futures as conc
import argparse
import platform
import signal

def is_windows():
    platname = platform.system().lower()
    return platname == 'windows' or 'mingw' in platname

tests_failed = []

parser = argparse.ArgumentParser()
parser.add_argument('--wrapper', default=None, dest='wrapper',
                    help='wrapper to run tests with (e.g. valgrind)')
parser.add_argument('--wd', default=None, dest='wd',
                    help='directory to cd into before running')
parser.add_argument('--suite', default=None, dest='suite',
                    help='Only run tests belonging to this suite.')
parser.add_argument('args', nargs='+')


class TestRun():
    def __init__(self, res, returncode, duration, stdo, stde, cmd):
        self.res = res
        self.returncode = returncode
        self.duration = duration
        self.stdo = stdo
        self.stde = stde
        self.cmd = cmd

def decode(stream):
    try:
        return stream.decode('utf-8')
    except UnicodeDecodeError:
        return stream.decode('iso-8859-1', errors='ignore')

def write_log(logfile, test_name, result_str, result):
    logfile.write(result_str + '\n\n')
    logfile.write('--- command ---\n')
    if result.cmd is None:
        logfile.write('NONE')
    else:
        logfile.write(' '.join(result.cmd))
    logfile.write('\n--- "%s" stdout ---\n' % test_name)
    logfile.write(result.stdo)
    logfile.write('\n--- "%s" stderr ---\n' % test_name)
    logfile.write(result.stde)
    logfile.write('\n-------\n\n')

def write_json_log(jsonlogfile, test_name, result):
    result = {'name' : test_name,
              'stdout' : result.stdo,
              'stderr' : result.stde,
              'result' : result.res,
              'duration' : result.duration,
              'returncode' : result.returncode,
              'command' : result.cmd}
    jsonlogfile.write(json.dumps(result) + '\n')

def run_with_mono(fname):
    if fname.endswith('.exe') and not is_windows():
        return True
    return False

def run_single_test(wrap, test):
    global tests_failed
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
    if len(wrap) > 0 and 'valgrind' in wrap[0]:
        wrap += test.valgrind_args
    if cmd is None:
        res = 'SKIP'
        duration = 0.0
        stdo = 'Not run because can not execute cross compiled binaries.'
        stde = ''
        returncode = -1
    else:
        cmd = wrap + cmd + test.cmd_args
        starttime = time.time()
        child_env = os.environ.copy()
        child_env.update(test.env)
        if len(test.extra_paths) > 0:
            child_env['PATH'] = child_env['PATH'] + ';'.join([''] + test.extra_paths)
        if is_windows():
            setsid = None
        else:
            setsid = os.setsid
        p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             env=child_env,
                             cwd=test.workdir,
                             preexec_fn=setsid)
        timed_out = False
        try:
            (stdo, stde) = p.communicate(timeout=test.timeout)
        except subprocess.TimeoutExpired:
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
        stde = decode(stde)
        if timed_out:
            res = 'TIMEOUT'
            tests_failed.append((test.name, stdo, stde))
        elif (not test.should_fail and p.returncode == 0) or \
            (test.should_fail and p.returncode != 0):
            res = 'OK'
        else:
            res = 'FAIL'
            tests_failed.append((test.name, stdo, stde))
        returncode = p.returncode
    return TestRun(res, returncode, duration, stdo, stde, cmd)

def print_stats(numlen, tests, name, result, i, logfile, jsonlogfile):
    startpad = ' '*(numlen - len('%d' % (i+1)))
    num = '%s%d/%d' % (startpad, i+1, len(tests))
    padding1 = ' '*(38-len(name))
    padding2 = ' '*(8-len(result.res))
    result_str = '%s %s  %s%s%s%5.2f s' % \
        (num, name, padding1, result.res, padding2, result.duration)
    print(result_str)
    write_log(logfile, name, result_str, result)
    write_json_log(jsonlogfile, name, result)

def drain_futures(futures):
    for i in futures:
        (result, numlen, tests, name, i, logfile, jsonlogfile) = i
        print_stats(numlen, tests, name, result.result(), i, logfile, jsonlogfile)

def filter_tests(suite, tests):
    if suite is None:
        return tests
    return [x for x in tests if suite in x.suite]

def run_tests(options, datafilename):
    logfile_base = 'meson-logs/testlog'
    if options.wrapper is None:
        wrap = []
        logfilename = logfile_base + '.txt'
        jsonlogfilename = logfile_base+ '.json'
    else:
        wrap = [options.wrapper]
        logfilename = logfile_base + '-' + options.wrapper.replace(' ', '_') + '.txt'
        jsonlogfilename = logfile_base + '-' + options.wrapper.replace(' ', '_') + '.json'
    logfile = open(logfilename, 'w')
    jsonlogfile = open(jsonlogfilename, 'w')
    logfile.write('Log of Meson test suite run on %s.\n\n' % datetime.datetime.now().isoformat())
    tests = pickle.load(open(datafilename, 'rb'))
    if len(tests) == 0:
        print('No tests defined.')
        return
    numlen = len('%d' % len(tests))
    varname = 'MESON_TESTTHREADS'
    if varname in os.environ:
        try:
            num_workers = int(os.environ[varname])
        except ValueError:
            print('Invalid value in %s, using 1 thread.' % varname)
            num_workers = 1
    else:
        num_workers = multiprocessing.cpu_count()
    executor = conc.ThreadPoolExecutor(max_workers=num_workers)
    futures = []
    filtered_tests = filter_tests(options.suite, tests)
    for i, test in enumerate(filtered_tests):
        if test.suite[0] == '':
            visible_name = test.name
        else:
            if options.suite is not None:
                visible_name = options.suite + ' / ' + test.name
            else:
                visible_name = test.suite[0] + ' / ' + test.name

        if not test.is_parallel:
            drain_futures(futures)
            futures = []
            res = run_single_test(wrap, test)
            print_stats(numlen, filtered_tests, visible_name, res, i, logfile, jsonlogfile)
        else:
            f = executor.submit(run_single_test, wrap, test)
            futures.append((f, numlen, filtered_tests, visible_name, i, logfile, jsonlogfile))
    drain_futures(futures)
    return logfilename

def run(args):
    global tests_failed
    tests_failed = [] # To avoid state leaks when invoked multiple times (running tests in-process)
    options = parser.parse_args(args)
    if len(options.args) != 1:
        print('Test runner for Meson. Do not run on your own, mmm\'kay?')
        print('%s [data file]' % sys.argv[0])
    if options.wd is not None:
        os.chdir(options.wd)
    datafile = options.args[0]
    logfilename = run_tests(options, datafile)
    returncode = 0
    if len(tests_failed) > 0:
        print('\nOutput of failed tests (max 10):')
        for (name, stdo, stde) in tests_failed[:10]:
            print("{} stdout:\n".format(name))
            print(stdo)
            print('\n{} stderr:\n'.format(name))
            print(stde)
            print('\n')
        returncode = 1
    print('\nFull log written to %s.' % logfilename)
    return returncode

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
