project('compiler_object_in_run_command', 'c')

foo = find_program('foo', required: true)
# This test only checks that the compiler object can be passed to
# run_command(). If the compiler has been launched, it is expected
# to output something either to stdout or to stderr.
result = run_command('echo', foo, '--version', check: false)

if result.stdout() == '' and result.stderr() == ''
  error('No output in stdout and stderr. Did the compiler run at all?')
endif
assert(result.stdout() == 'bar baz --version\n')
