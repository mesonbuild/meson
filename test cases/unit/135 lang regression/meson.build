project('depfallback', 'cpp')

dep = dependency('pcre2')

lib = static_library('intlib', 'intlib.cpp',
  dependencies: dep)

executable('p2test', 'p2test.cpp',
  link_with: lib)
