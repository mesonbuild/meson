# SPDX-license-identifier: Apache-2.0

project('sub2')

prog = find_program('script.py', version : '== 2.0.0')

r = run_command(prog, '--version')

assert(r.stdout().strip() == 'script.py 2.0.0', r.stdout())