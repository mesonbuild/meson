project('override_options_std_cpp', 'cpp')

dep = dependency('std_cpp_11')

executable('prog', 'prog.cpp', dependencies : [dep], override_options : ['cpp_std=c++17'])
