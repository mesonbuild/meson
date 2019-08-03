project('custom target input extracted objects', 'c')

comp = find_program('exe_generator.py')
run = find_program('exe_runner.py')

if host_machine.system() == 'windows'
  outputname = 'prog.exe'
else
  outputname = 'prog'
endif

cc = meson.get_compiler('c').cmd_array().get(-1)

subdir('libdir')
subdir('progdir')

test('objgen', run, args: e)
