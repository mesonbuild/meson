project('wxwidgets test', 'cpp', default_options : ['cpp_std=c++11'])

wxd = dependency('wxwidgets', version : '>=5', required : false)
wxd = dependency('wxwidgets', version : '>=3.0.0', required : false)

if wxd.found()
  wp = executable('wxprog', 'wxprog.cpp', dependencies : wxd)

  test('wxtest', wp)
endif
