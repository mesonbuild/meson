project('cmake_set_opt', ['c', 'cpp'])

cm   = import('cmake')
opts = cm.subproject_options()

opts.add_cmake_defines({'SOME_CMAKE_VAR': 'something', 'SOME_OTHER_VAR': true})

opts.set_override_option('cpp_std', 'c++11')                        # Global is C++11
opts.set_override_option('cpp_std', 'c++14', target: 'cmModLib++')  # Override it with C++14 for cmModLib++

opts.append_compile_args('cpp', '-DMESON_GLOBAL_FLAG=1')
opts.append_compile_args('cpp', ['-DMESON_SPECIAL_FLAG1=1', ['-DMESON_SPECIAL_FLAG2=1']], target: 'cmModLib++')
opts.append_compile_args('cpp', '-DMESON_MAGIC_INT=42',                                   target: 'cmModLib++')
opts.append_compile_args('cpp', [[[['-DMESON_MAGIC_INT=20']]]],                           target: 'cmTestLib')

opts.set_install(false)
opts.set_install(true, target: 'testEXE')

sp   = cm.subproject('cmOpts', options: opts)
dep1 = sp.dependency('cmModLib++')
dep2 = sp.dependency('cmTestLib')

exe1 = executable('main', ['main.cpp'], dependencies: [dep1, dep2])
test('test1', exe1)
