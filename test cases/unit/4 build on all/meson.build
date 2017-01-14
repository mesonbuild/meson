project('build on all', 'c')

py3_mod = import('python3')
py3 = py3_mod.find_python()

executable('fooprog', 'foo.c', build_on_all : false)
comp = files('mygen.py')
mytarget = custom_target('gendat',
  output : 'generated.dat',
  input : 'source.txt',
  command : [py3] + comp + ['@INPUT@', '@OUTPUT@'],
  build_on_all : true,
)
