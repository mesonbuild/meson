project('windows_galore', ['c', 'cpp'])

if host_machine.system() != 'windows'
  error('MESON_SKIP_TEST: This test requires Windows')
endif

cm = import('cmake')

cm_opts = cm.subproject_options()
sub_pro = cm.subproject('subproj', options: cm_opts)

prefix = get_option('prefix')

explicit_libs = sub_pro.dependency('explicit_libs')
exe1 = executable('main', ['main.cpp'], dependencies: [explicit_libs])
test('test1', exe1)
