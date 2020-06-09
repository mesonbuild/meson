project('threads', 'cpp', 'c',
  default_options : ['cpp_std=c++11'])

threaddep = dependency('threads')

cc = meson.get_compiler('c')

args = []
if threaddep.get_variable(meson : 'model') == 'win32'
  args += '-DHAVE_WIN32_THREADS'
elif threaddep.get_variable(meson : 'model') == 'posix'
  args += '-DHAVE_POSIX_THREADS'
endif

test('cppthreadtest',
  executable('cppthreadprog', 'threadprog.cpp',
    dependencies : threaddep
  )
)

test('cthreadtest',
  executable('cthreadprog', 'threadprog.c',
    dependencies : threaddep,
    c_args : args,
  )
)
