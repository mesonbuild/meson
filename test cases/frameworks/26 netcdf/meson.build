project('netcdf_test', 'c', 'cpp')

if build_machine.system() == 'darwin'
  error('MESON_SKIP_TEST: NetCDF CI image not setup for OSX.')
endif

if build_machine.system() == 'cygwin'
  error('MESON_SKIP_TEST: NetCDF CI image not setup for Cygwin.')
endif


# --- C tests
NCc = dependency('netcdf', language : 'c', required : false)
if not NCc.found()
  error('MESON_SKIP_TEST: NetCDF C library not found, skipping NetCDF framework tests.')
endif
exec = executable('exec', 'main.c', dependencies : NCc)

test('NetCDF C', exec)

# --- C++ tests
NCcpp = dependency('netcdf', language : 'cpp', required : false)
if NCcpp.found()
  execpp = executable('execpp', 'main.cpp', dependencies : NCcpp)
  test('NetCDF C++', execpp)
endif

# --- Fortran tests
if build_machine.system() != 'windows'
  add_languages('fortran')

  NCf = dependency('netcdf', language : 'fortran', required : false)
  if NCf.found()
    exef = executable('exef', 'main.f90', dependencies : NCf)

    test('NetCDF Fortran', exef)
  endif
endif

# Check we can apply a version constraint
if NCc.version() != 'unknown'
  dependency('netcdf', version: '>=@0@'.format(NCc.version()))
endif
