project('threads', 'cpp', 'c',
  default_options : ['cpp_std=c++11'])

threaddep = dependency('threads')

test('cppthreadtest',
  executable('cppthreadprog', 'threadprog.cpp',
    dependencies : threaddep
  )
)

test('cthreadtest',
  executable('cthreadprog', 'threadprog.c',
    dependencies : threaddep
  )
)
