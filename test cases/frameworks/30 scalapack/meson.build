project('test scalapack', 'c')

cc = meson.get_compiler('c')

mpiexec = find_program('mpiexec', required: false)
if not mpiexec.found()
  error('MESON_SKIP_TEST: mpiexec not found')
endif

mpi_c = dependency('mpi', language: 'c', required: false)
if not mpi_c.found()
  error('MESON_SKIP_TEST: MPI library not available')
endif

# examples can run with any number of MPI images.
mpi_args = ['-np', '1']

scalapack = dependency('scalapack', required: false)
if not scalapack.found()
  error('MESON_SKIP_TEST: scalapack library not available')
endif

# https://software.intel.com/en-us/mkl-developer-reference-c-scalapack-routines
c_exe = executable('scalapack_c', 'main.c',
  dependencies: [scalapack, mpi_c])
test('scalapack_c', mpiexec,
  args: [mpi_args, c_exe],
  timeout: 30)

if add_languages('fortran')
  mpi_f = dependency('mpi', language: 'fortran', required: false)
  if not mpi_f.found()
    error('MESON_SKIP_TEST: MPI Fortran library not available')
  endif

  # https://software.intel.com/en-us/mkl-developer-reference-fortran-scalapack-routines
  f_exe = executable('scalapack_fortran', 'main.f90',
    dependencies: [scalapack, mpi_f])
  test('scalapack_fortran', mpiexec,
    args: [mpi_args, f_exe],
    timeout: 30)
endif