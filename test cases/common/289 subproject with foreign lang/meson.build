project('depfallback', 'cpp')

subp = subproject('pcre2')

lib = static_library('intlib', 'intlib.cpp',
  link_with: subp.get_variable('pcre2_lib'))

executable('p2test', 'p2test.cpp',
  link_with: lib)
