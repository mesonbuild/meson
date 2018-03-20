project(
  'assert removed test',
  'cpp',
  default_options : [
    'buildtype=release',
    'b_ndebug=if-release',
  ])

# Idea behind this test is to see that assert() is
# removed and the side-effects of its argument function
# are not observed

# Credits for idea go to sarum9in

libA = library('A', 'libA.cpp')

main_exe = executable('main', 'main.cpp', link_with : libA)
test('main test', main_exe)
