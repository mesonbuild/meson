project('dynamic_fortran', 'fortran')

if meson.get_compiler('fortran').get_id() == 'intel-cl'
  error('MESON_SKIP_TEST: Windows ifort does not use shared_library in a sane way')
  # !DEC$ ATTRIBUTES DLLEXPORT must be used!
  # https://software.intel.com/en-us/node/535306
endif

dynamic = shared_library('dynamic', 'dynamic.f90')
exe = executable('test_exe', 'main.f90', link_with : dynamic)
test('dynamic-fortran', exe)
