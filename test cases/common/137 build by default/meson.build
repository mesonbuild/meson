project('build on all', 'c')

py3_mod = import('python3')
py3 = py3_mod.find_python()

executable('fooprog', 'foo.c', build_by_default : false)
comp = files('mygen.py')
mytarget = custom_target('gendat',
  output : 'generated.dat',
  input : 'source.txt',
  command : [py3] + comp + ['@INPUT@', '@OUTPUT@'],
  build_by_default : true,
)

ct_output = join_paths(meson.build_root(), 'generated.dat')
exe_output = join_paths(meson.build_root(), 'fooprog')
if host_machine.system() == 'windows'
  exe_output += '.exe'
endif

ct_exists_exe_nexists = 'import os.path, sys; sys.exit(not os.path.exists(sys.argv[1]) and os.path.exists(sys.argv[2]))'

test('check-build-by-default', py3,
     args : ['-c', ct_exists_exe_nexists, ct_output, exe_output])
