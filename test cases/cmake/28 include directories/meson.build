project('include directories test', 'c')

cm = import('cmake')

sub_pro = cm.subproject('cmTest')
sub_dep = sub_pro.dependency('cmTest')

missing_inc_dir_arg = '-Werror=missing-include-dirs'
has_missing_inc_dir = meson.get_compiler('c').has_argument(missing_inc_dir_arg)
if not has_missing_inc_dir
  error('MESON_SKIP_TEST: Compiler does not support ' + missing_inc_dir_arg)
else
  add_project_arguments(missing_inc_dir_arg, language: 'c')
endif

exe1 = executable('exe1', ['main.c'], dependencies: [sub_dep])
test('test1', exe1)
