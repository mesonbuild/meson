project('dependency include path', ['c', 'cpp'])

subdir('subfolder')

dep = declare_dependency(include_directories : 'incdir',
                         dependencies : subfolder_dep,
                         compile_args : ['-I/dash/i', '-isystem=/dash/isystem'])


if build_machine.system() == 'windows'
  subfolder_inc = 'subfolder\\headers'
else
  subfolder_inc = 'subfolder/headers'
endif
assert(dep.get_include_paths() == ['incdir', '/dash/i', '/dash/isystem', subfolder_inc], 'dep.get_include_paths() failed.')

