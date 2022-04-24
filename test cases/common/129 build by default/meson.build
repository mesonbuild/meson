project('build on all', 'c')

py_mod = import('python')
py3 = py_mod.find_installation()

executable('fooprog', 'foo.c',
    build_by_default : false,
)

executable('barprog', 'foo.c',
    build_by_default : false,
)

comp = files('mygen.py')
checkexists = files('checkexists.py')

mytarget = custom_target('gendat1',
  output : 'generated1.dat',
  input : 'source.txt',
  command : [py3] + comp + ['@INPUT@', '@OUTPUT@'],
  build_by_default : true,
)

mytarget = custom_target('gendat2',
  output : 'generated2.dat',
  input : 'source.txt',
  command : [py3] + comp + ['@INPUT@', '@OUTPUT@'],
  build_by_default : true,
  build_always : false,
)

ct1_output = join_paths(meson.build_root(), 'generated1.dat')
ct2_output = join_paths(meson.build_root(), 'generated2.dat')
exe1_output = join_paths(meson.build_root(), 'fooprog')
exe2_output = join_paths(meson.build_root(), 'barprog')

if host_machine.system() == 'windows'
  exe1_output += '.exe'
  exe2_output += '.exe'
endif

test('check-build-by-default', py3,
     args : [checkexists,
        ct1_output, ct2_output, '--not', exe1_output, exe2_output])
