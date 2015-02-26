project('wxwidgets test', 'cpp')

add_global_arguments('-std=c++11', language : 'cpp')

wxd = dependency('wxwidgets', version : '>=3.0.0')

wp = executable('wxprog', 'wxprog.cpp',
dependencies : wxd)

test('wxtest', wp)
