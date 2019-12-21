project('hdf5_framework', 'c')

# NOTE: all HDF5 languages must have HDF5 C library working.

# --- C tests
h5c = dependency('hdf5', language : 'c', required : false)
if not h5c.found()
  error('MESON_SKIP_TEST: HDF5 C library not found.')
endif
exec = executable('exec', 'main.c', dependencies : h5c)
test('HDF5 C', exec, timeout: 30)

# --- C++ tests
if add_languages('cpp', required: false)
  h5cpp = dependency('hdf5', language : 'cpp', required : false, disabler: true)
  execpp = executable('execpp', 'main.cpp', dependencies : h5cpp)
  test('HDF5 C++', execpp, timeout: 30)
endif

# --- Fortran tests
if add_languages('fortran', required: false)
  h5f = dependency('hdf5', language : 'fortran', required : false, disabler: true)
  exef = executable('exef', 'main.f90', dependencies : h5f)
  test('HDF5 Fortran', exef, timeout: 30)
endif

# Check we can apply a version constraint
if h5c.version() != 'unknown'
  dependency('hdf5', version: '>=@0@'.format(h5c.version()))
endif
