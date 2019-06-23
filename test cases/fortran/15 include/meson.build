project('Inclusive', 'fortran',
  meson_version: '>= 0.51.1')

hier_exe = executable('include_hierarchy', 'include_hierarchy.f90')
test('Fortran include file hierarchy', hier_exe)

syntax_exe = executable('include_syntax', 'include_syntax.f90')
test('Fortran include file syntax', syntax_exe)