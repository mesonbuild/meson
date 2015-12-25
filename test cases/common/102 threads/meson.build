project('threads', 'cpp', 'c')

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
