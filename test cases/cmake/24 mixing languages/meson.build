# Explicitly require PIE so that mixing compilers with different defaults for
# whether to use PIE works.
project('CMake mix', ['c', 'cpp'],
  default_options: ['b_pie=true'])

if not add_languages('objc', required : false)
  error('MESON_SKIP_TEST: No ObjC compiler')
endif

objc = meson.get_compiler('objc')
c = meson.get_compiler('c')
if c.get_argument_syntax() != objc.get_argument_syntax()
  error('MESON_SKIP_TEST: cmake cannot mix compiler types on Windows')
endif

cm = import('cmake')

sub_pro = cm.subproject('cmTest')
sub_dep = sub_pro.dependency('cmTest', include_type: 'system')

exe1 = executable('exe1', ['main.c'], dependencies: [sub_dep])
test('test1', exe1)
