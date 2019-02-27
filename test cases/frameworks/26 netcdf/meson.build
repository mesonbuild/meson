project('netcdf_test', 'c', 'cpp')


# --- C tests
nc_c = dependency('netcdf', language : 'c', required : false)
if not nc_c.found()
  error('MESON_SKIP_TEST: NetCDF C library not found, skipping NetCDF framework tests.')
endif
exec = executable('exec', 'main.c', dependencies : nc_c)

test('NetCDF C', exec)

# --- C++ tests
nc_cpp = dependency('netcdf', language : 'cpp', required : false)
if nc_cpp.found()
  execpp = executable('execpp', 'main.cpp', dependencies : nc_cpp)
  test('NetCDF C++', execpp)
endif

# --- Fortran tests
if build_machine.system() != 'windows'
  add_languages('fortran')

  nc_f = dependency('netcdf', language : 'fortran', required : false)
  if nc_f.found()
    exef = executable('exef', 'main.f90', dependencies : nc_f)

    test('NetCDF Fortran', exef)
  endif
endif

# Check we can apply a version constraint
if nc_c.version() != 'unknown'
  dependency('netcdf', version: '>=@0@'.format(nc_c.version()))
endif
