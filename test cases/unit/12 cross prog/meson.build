project('cross find program', 'c')

native_exe = find_program('sometool.py', native : true)
cross_exe = find_program('sometool.py')

native_out = run_command(native_exe).stdout().strip()
cross_out = run_command(cross_exe).stdout().strip()

assert(native_out == 'native',
  'Native output incorrect:' + native_out)
assert(cross_out == 'cross',
  'Cross output incorrect:' + cross_out)
