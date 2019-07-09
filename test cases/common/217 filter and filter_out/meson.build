project('filter_and_filter_out', 'cpp',
  version : '1.0.0',
  default_options : ['warning_level=3',
                     'cpp_std=c++14'])

src = [
  'lib1/cpplib.cpp',
  'lib2/cpplib.cpp',
  'lib3/cpplib.cpp',
]
message('All source list contains: @0@'.format(src))

lib1_src = filter(src, pattern: 'lib1/.*\.cpp')
not1_or_2_src = filter_out(src, pattern: 'lib1|lib2/.*\.cpp')

message('Building lib1 with @0@'.format(lib1_src))
lib1 = shared_library('lib1', lib1_src)

message('Building libnot1_or_2 with @0@'.format(not1_or_2_src))
libnot1_or_2 = shared_library('libnot1_or_2', not1_or_2_src)
