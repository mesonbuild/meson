project('d and c++', 'd', 'cpp')

cpp = meson.get_compiler('cpp')
dc = meson.get_compiler('d')

if cpp.get_id() == 'clang' and dc.get_id() == 'gcc'
  error('MESON_SKIP_TEST combining Clang C++ with GDC produces broken executables.')
endif

e1 = executable('dcpp', 'dmain.d', 'libfile.cpp')
test('dcpp', e1)

e2 = executable('cppd', 'cppmain.cpp', 'libfile.d')
test('cppd', e2)
