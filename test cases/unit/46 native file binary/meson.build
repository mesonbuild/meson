project('test project')

case = get_option('case')

if case == 'find_program'
  prog = find_program('bash')
  result = run_command(prog, ['--version'])
  assert(result.stdout().strip().endswith('12345'), 'Didn\'t load bash from config file')
endif
