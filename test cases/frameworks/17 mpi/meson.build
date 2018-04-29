project('mpi', 'c', 'cpp')

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
  # C++ MPI not supported by MS-MPI used on AppVeyor.
  mpicpp = dependency('mpi', language : 'cpp')
  execpp = executable('execpp',
    'main.cpp',
    dependencies : [mpicpp])

  test('MPI C++', execpp)
endif

# OpenMPI is broken with Fortran on Ubuntu Artful.
# Remove this once the following bug has been fixed:
#
# https://bugs.launchpad.net/ubuntu/+source/gcc-defaults/+bug/1727474

ubudetector = find_program('is_broken_ubuntu.py')
uburesult = run_command(ubudetector)

if uburesult.returncode() != 0 and add_languages('fortran', required : false)
  mpifort = dependency('mpi', language : 'fortran')
  exef = executable('exef',
    'main.f90',
    dependencies : [mpifort])

  test('MPI Fortran', exef)
endif
