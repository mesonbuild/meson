project('hdf5_test', 'c', 'cpp')

if build_machine.system() == 'darwin'
  error('MESON_SKIP_TEST: HDF5 CI image not setup for OSX.')
endif

if build_machine.system() == 'cygwin'
  error('MESON_SKIP_TEST: HDF5 CI image not setup for Cygwin.')
endif


# --- C tests
h5c = dependency('hdf5', language : 'c', required : false)
if not h5c.found()
  error('MESON_SKIP_TEST: HDF5 not found, skipping.')
endif
exec = executable('exec', 'main.c',
  dependencies : h5c)

test('HDF5 C', exec)

# --- C++ tests
h5cpp = dependency('hdf5', language : 'cpp')
execpp = executable('execpp', 'main.cpp',
  dependencies : h5cpp)

test('HDF5 C++', execpp)


# --- Fortran tests
if build_machine.system() != 'windows'
  add_languages('fortran')

  h5f = dependency('hdf5', language : 'fortran')
  exef = executable('exef', 'main.f90',
    dependencies : h5f)

  test('HDF5 Fortran', exef)
endif

# Check we can apply a version constraint
if h5c.version() != 'unknown'
  dependency('hdf5', version: '>=@0@'.format(h5c.version()))
endif
