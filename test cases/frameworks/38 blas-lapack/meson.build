project('test blas and lapack', 'c')

# OpenBLAS LP64 and ILP64
openblas_dep = dependency('openblas',
  modules: [
    'interface: lp64',
    'cblas',
    'lapack',
  ],
  required: false,
)
openblas64_dep = dependency('openblas',
  modules: [
    'interface: ilp64',
    'cblas',
    'lapack',
  ],
  required: false,
)

# Accelerate LP64 and ILP64
accelerate_dep = dependency('accelerate',
  modules: [
    'interface: lp64',
    'cblas',
    'lapack',
  ],
  required: false,
)
accelerate64_dep = dependency('accelerate',
  modules: [
    'interface: ilp64',
    'cblas',
    'lapack',
  ],
  required: false,
)

# MKL LP64 and ILP64
mkl_dep = dependency('mkl',
  modules: [
    'interface: lp64',
    'cblas',
    'lapack',
  ],
  required: false,
)
mkl64_dep = dependency('mkl',
  modules: [
    'interface: ilp64',
    'cblas',
    'lapack',
  ],
  required: false,
)


if not openblas_dep.found() and not openblas64_dep.found() and not accelerate_dep.found() and not mkl_dep.found()
  error('MESON_SKIP_TEST: no BLAS/LAPACK libraries available')
endif

deps = {
  'openblas': openblas_dep,
  'openblas64': openblas64_dep,
  'accelerate': accelerate_dep,
  'accelerate64': accelerate64_dep,
  'mkl': mkl_dep,
  'mkl64': mkl64_dep,
}

foreach name, dep : deps
  if dep.found()
    blas_interface = dep.get_variable('interface')
    symbol_suffix = dep.get_variable('symbol_suffix')
    blas_c_args = ['-DBLAS_SYMBOL_SUFFIX=' + symbol_suffix]
    if blas_interface == 'ilp64'
      blas_c_args += ['-DHAVE_BLAS_ILP64']
      if 'openblas' in dep.name()
        blas_c_args += ['-DOPENBLAS_ILP64_NAMING_SCHEME']
      endif
    elif blas_interface != 'lp64'
      error(f'no interface var for %name% dependency!')
    endif

    c_exe = executable('cblas_lapack_c_' + blas_interface,
      'cblas_lapack.c',
      c_args: blas_c_args,
      dependencies: [dep]
    )
    test('cblas_lapack_dep_c', c_exe, timeout: 30)

    if add_languages('fortran', required: false)
      f_exe = executable('cblas_lapack_fortran_' + blas_interface,
        'main.f90',
        dependencies: [dep]
      )
      test('cblas_lapack_dep_fortran', f_exe, timeout: 30)
    endif
  endif
endforeach
