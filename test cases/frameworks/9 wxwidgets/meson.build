project('wxwidgets test', 'cpp')

wxd = dependency('wxwidgets', version : '>=3.0.0')

wp = executable('wxprog', 'wxprog.cpp',
dependencies : wxd)

test('wxtest', wp)
