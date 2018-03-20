project(
  'assert retained test',
  'cpp',
  default_options : [
    'buildtype=debugoptimized',
    'b_ndebug=if-release',
  ])

# Idea behind this test is to see that assert() is
# *not* removed and calls a function with side-effects
# This acts as a negative control for adding -DNDEBUG

# Credits for idea go to sarum9in

libA = library('A', 'libA.cpp')

main_exe = executable('main', 'main.cpp', link_with : libA)
test('main test', main_exe)
