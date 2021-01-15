# SPDX-license-identifier: Apache-2.0

project('sub1')

prog = find_program('script.py', version : '== 1.0.0')
r = run_command(prog, '--version')
assert(r.stdout().strip() == 'script.py 1.0.0', r.stdout())

prog = find_program('script.py')
r = run_command(prog, '--version')
assert(r.stdout().strip() == 'script.py 1.0.0', r.stdout())