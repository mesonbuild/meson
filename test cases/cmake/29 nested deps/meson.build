project('cmakeSubTest', ['c', 'cpp'], default_options: ['cpp_std=c++14'])

cm = import('cmake')
opts = cm.subproject_options()

if get_option('default_library') == 'static'
  opts.add_cmake_defines({'DEFAULT_LIBRARY': 'STATIC'})
elif get_option('default_library') == 'shared'
  opts.add_cmake_defines({'DEFAULT_LIBRARY': 'SHARED'})
else
  error('Specify default_library')
endif

sub_pro = cm.subproject('cmMod', options: opts)
sub_dep = sub_pro.dependency('cmModLib++')

exe1 = executable('main', ['main.cpp'], dependencies: [sub_dep])
test('test1', exe1)
