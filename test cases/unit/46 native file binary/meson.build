project('test project')

case = get_option('case')

if case == 'find_program'
  prog = find_program('bash')
  result = run_command(prog, ['--version'])
  assert(result.stdout().strip().endswith('12345'), 'Didn\'t load bash from config file')
elif case == 'config_dep'
  add_languages('cpp')
  dep = dependency('llvm')
  assert(dep.get_configtool_variable('version').endswith('12345'), 'Didn\'t load llvm from config file')
endif
