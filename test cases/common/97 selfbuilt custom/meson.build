project('selfbuilt custom', 'cpp')

# Build an exe and use it in a custom target
# whose output is used to build a different exe.

tool = executable('tool', 'tool.cpp')

hfile = custom_target('datah',
  output : 'data.h',
  input : 'data.dat',
  command : [tool, '@INPUT@', '@OUTPUT@'],
)

main = executable('mainprog', 'mainprog.cpp', hfile)

test('maintest', main)
