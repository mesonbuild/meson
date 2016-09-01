#!/usr/bin/env python3

# Copyright 2015 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess, sys, os, argparse
import pickle, statistics, json
from . import meson_test

parser = argparse.ArgumentParser()
parser.add_argument('--wd', default=None, dest='wd',
                    help='directory to cd into before running')
parser.add_argument('args', nargs='+')

def print_stats(numlen, num_tests, name, res, i, duration, stdev):
    startpad = ' '*(numlen - len('%d' % (i+1)))
    num = '%s%d/%d' % (startpad, i+1, num_tests)
    padding1 = ' '*(38-len(name))
    padding2 = ' '*(8-len(res))
    result_str = '%s %s  %s%s%s%5.5f s +- %5.5f s' % \
        (num, name, padding1, res, padding2, duration, stdev)
    print(result_str)
#    write_json_log(jsonlogfile, name, result)

def print_json_log(jsonlogfile, rawruns, test_name, i):
    jsonobj = {'name' : test_name}
    runs = []
    for r in rawruns:
        runobj = {'duration': r.duration,
                  'stdout': r.stdo,
                  'returncode' : r.returncode,
                  'duration' : r.duration}
        if r.stde:
            runobj['stderr'] = r.stde
        runs.append(runobj)
    jsonobj['runs'] = runs
    jsonlogfile.write(json.dumps(jsonobj) + '\n')
    jsonlogfile.flush()

def run_benchmarks(options, datafile):
    failed_tests = 0
    logfile_base = 'meson-logs/benchmarklog'
    jsonlogfilename = logfile_base+ '.json'
    with open(datafile, 'rb') as f:
        tests = pickle.load(f)
    num_tests = len(tests)
    if num_tests == 0:
        print('No benchmarks defined.')
        return 0
    iteration_count = 5
    wrap = [] # Benchmarks on cross builds are pointless so don't support them.
    with open(jsonlogfilename, 'w') as jsonlogfile:
        for i, test in enumerate(tests):
            runs = []
            durations = []
            failed = False
            for _ in range(iteration_count):
                res = meson_test.run_single_test(wrap, test)
                runs.append(res)
                durations.append(res.duration)
                if res.returncode != 0:
                    failed = True
            mean = statistics.mean(durations)
            stddev = statistics.stdev(durations)
            if failed:
                resultstr = 'FAIL'
                failed_tests += 1
            else:
                resultstr = 'OK'
            print_stats(3, num_tests, test.name, resultstr, i, mean, stddev)
            print_json_log(jsonlogfile, runs, test.name, i)
    print('\nFull log written to meson-logs/benchmarklog.json.')
    return failed_tests

def run(args):
    global failed_tests
    options = parser.parse_args(args)
    if len(options.args) != 1:
        print('Benchmark runner for Meson. Do not run on your own, mmm\'kay?')
        print('%s [data file]' % sys.argv[0])
    if options.wd is not None:
        os.chdir(options.wd)
    datafile = options.args[0]
    returncode = run_benchmarks(options, datafile)
    return returncode

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
