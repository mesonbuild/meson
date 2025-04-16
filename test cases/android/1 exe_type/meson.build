project('android exe type', 'c')
fs = import('fs')

e = executable('executable', 'exe_type.c',
  android_exe_type : 'executable')
a = executable('application', 'exe_type.c',
  android_exe_type : 'application')

if fs.name(e.full_path()).contains('.')
  error('Executable with exe_type `executable` did have expected filename')
endif

if not fs.name(a.full_path()).startswith('lib') or not fs.name(a.full_path()).endswith('.so')
  error('Executable with exe_type `application` did not have expected filename')
endif
