project('mpi', 'c', 'cpp', default_options: ['b_asneeded=false'])

cc = meson.get_compiler('c')

if build_machine.system() == 'windows' and cc.get_id() != 'msvc'
  error('MESON_SKIP_TEST: MPI not available on Windows without MSVC.')
endif

mpic = dependency('mpi', language : 'c', required : false)
if not mpic.found()
  error('MESON_SKIP_TEST: MPI not found, skipping.')
endif
exec = executable('exec',
  'main.c',
  dependencies : [mpic])

test('MPI C', exec)

if build_machine.system() != 'windows'
  # C++ MPI not supported by MS-MPI
  mpicpp = dependency('mpi', language : 'cpp')
  execpp = executable('execpp',
    'main.cpp',
    dependencies : [mpicpp])

  test('MPI C++', execpp)
endif

# One of few feasible ways to use MPI for Fortran on Windows is via Intel compilers.
if build_machine.system() != 'windows' or cc.get_id() == 'intel'
  if add_languages('fortran', required : false)
    mpifort = dependency('mpi', language : 'fortran')

    exef = executable('exef',
    'main.f90',
    dependencies : [mpifort])

    test('MPI Fortran', exef)
  endif
endif

# Check we can apply a version constraint
if mpic.version() != 'unknown'
  dependency('mpi', version: '>=@0@'.format(mpic.version()))
endif
