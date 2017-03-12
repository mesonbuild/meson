project('cpp std override', 'cpp',
  default_options : 'cpp_std=c++03')

executable('plain', 'progp.cpp',
  override_options : 'cpp_std=none')
executable('v03', 'prog03.cpp')
executable('v11', 'prog11.cpp',
  override_options : 'cpp_std=c++11')
