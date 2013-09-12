#!/usr/bin/env python3

# Copyright 2013 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, subprocess, time, datetime, pickle
from optparse import OptionParser

parser = OptionParser()
parser.add_option('--wrapper', default=None, dest='wrapper',
                  help='wrapper to run tests with (e.g. valgrind)')

class TestRun():
    def __init__(self, res, duration, stdo, stde):
        self.res = res
        self.duration = duration
        self.stdo = stdo
        self.stde = stde

def write_log(logfile, test_name, result_str, stdo, stde):
    logfile.write(result_str + '\n\n')
    logfile.write('--- "%s" stdout ---\n' % test_name)
    logfile.write(stdo)
    logfile.write('\n--- "%s" stderr ---\n' % test_name)
    logfile.write(stde)
    logfile.write('\n-------\n\n')

def run_single_test(wrap, fname, is_cross, exe_runner):
    if is_cross:
        if exe_runner is None:
            # 'Can not run test on cross compiled executable 
            # because there is no execute wrapper.
            cmd = None
        else:
            cmd = [exe_runner, fname]
    else:
        cmd = [fname]
    if cmd is None:
        res = 'SKIP'
        duration = 0.0
        stdo = 'Not run because can not execute cross compiled binaries.'
        stde = ''
    else:
        cmd = wrap + cmd
        starttime = time.time()
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdo, stde) = p.communicate()
        endtime = time.time()
        duration = endtime - starttime
        stdo = stdo.decode()
        stde = stde.decode()
        if p.returncode == 0:
            res = 'OK'
        else:
            res = 'FAIL'
    return TestRun(res, duration, stdo, stde)

def run_tests(options, datafilename):
    logfile_base = 'meson-logs/testlog'
    if options.wrapper is None:
        wrap = []
        logfilename = logfile_base + '.txt'
    else:
        wrap = [options.wrapper]
        logfilename = logfile_base + '-' + options.wrapper.replace(' ', '_') + '.txt'
    logfile = open(logfilename, 'w')
    logfile.write('Log of Meson test suite run on %s.\n\n' % datetime.datetime.now().isoformat())
    tests = pickle.load(open(datafilename, 'rb'))
    numlen = len('%d' % len(tests))
    for i, test in enumerate(tests):
        name = test[0]
        fname = test[1]
        is_cross = test[2]
        exe_runner = test[3]
        is_parallel = True
        result = run_single_test(wrap, fname, is_cross, exe_runner)
        startpad = ' '*(numlen - len('%d' % (i+1)))
        num = '%s%d/%d' % (startpad, i+1, len(tests))
        padding1 = ' '*(40-len(name))
        padding2 = ' '*(5-len(result.res))
        result_str = '%s %s%s%s%s(%5.2f s)' % \
            (num, name, padding1, result.res, padding2, result.duration)
        print(result_str)
        write_log(logfile, name, result_str, result.stdo, result.stde)
    print('\nFull log written to %s.' % logfilename)

if __name__ == '__main__':
    (options, args) = parser.parse_args(sys.argv)
    if len(args) != 2:
        print('Test runner for Meson. Do not run on your own, mmm\'kay?')
        print('%s [data file]' % sys.argv[0])
    datafile = args[1]
    run_tests(options, datafile)
