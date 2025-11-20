project('test blas and lapack', 'c')

has_fortran = add_languages('fortran', required: false)

found_any = false
foreach name : ['openblas', 'accelerate', 'flexiblas', 'mkl', 'netlib']
  foreach interface : ['lp64', 'ilp64']
    # we treat 'sdl' here since it implies lp64+iomp, so we can avoid one
    # level of nesting
    foreach threading : ['seq', 'iomp', 'gomp', 'tbb', 'sdl']
      modules = [f'interface: @interface@']

      # threading and sdl are only relevant to mkl
      if name == 'mkl'
        if threading == 'sdl'
          # sdl is valid only for lp64
          if interface != 'lp64'
            continue
          endif
          modules += ['sdl: true']
        else
          modules += [f'threading: @threading@']
        endif
      elif threading != 'seq'
        continue
      endif

      # for netlib, we need to query cblas & lapack separately
      if name == 'netlib'
        blas = dependency('blas',
          modules: modules + ['cblas'],
          required: false,
        )
        lapack = dependency('lapack',
          modules: modules + ['lapack', 'lapacke'],
          required: false,
        )
        if not blas.found() or not lapack.found()
          continue
        endif
        foreach var : ['interface', 'symbol_suffix']
          assert(blas.get_variable(var) == lapack.get_variable(var))
        endforeach
        deps = [blas, lapack]
      else
        dep = dependency(name,
          modules: modules + ['cblas', 'lapack', 'lapacke'],
          required: false,
        )
        if not dep.found()
          continue
        endif
        deps = [dep]
      endif

      found_any = true
      blas_interface = deps[0].get_variable('interface')
      symbol_suffix = deps[0].get_variable('symbol_suffix')
      found_names = []
      foreach dep : deps
        found_names += [dep.name()]
      endforeach
      message(f'Found @name@ @blas_interface@ @threading@: @found_names@; symbol suffix: @symbol_suffix@')
      assert(blas_interface == interface)

      blas_c_args = ['-DBLAS_SYMBOL_SUFFIX=' + symbol_suffix]
      if blas_interface == 'ilp64'
        blas_c_args += ['-DHAVE_BLAS_ILP64']
        if 'openblas' in dep.name()
          blas_c_args += ['-DOPENBLAS_ILP64_NAMING_SCHEME']
        endif
      elif blas_interface != 'lp64'
        error(f'no interface var for @name@ dependency!')
      endif

      exe_suffix = f'@name@_@interface@_@threading@'
      c_exe = executable(f'cblas_lapack_@exe_suffix@_c',
        'cblas_lapack.c',
        c_args: blas_c_args,
        dependencies: deps
      )
      test(f'cblas_lapack_dep_@exe_suffix@_c', c_exe, timeout: 30)

      # TODO: mkl-ilp64 fortran executable segfaults frequently
      # netlib fortran executables too
      if has_fortran
        fc_id = meson.get_compiler('fortran').get_id()
        fc_args = []
        if fc_id == 'gcc'
          # TODO: why is netlib giving us ilp64?
          if interface == 'ilp64' or name == 'netlib'
            fc_args += ['-fdefault-integer-8']
          endif
        else
          error(f'Unknown Fortran compiler @fc_id@')
        endif
        f_exe = executable(f'cblas_lapack_@exe_suffix@_fortran',
          'main.f90',
          dependencies: deps,
          fortran_args: fc_args,
        )
        test(f'cblas_lapack_dep_@exe_suffix@_fortran', f_exe, timeout: 30)
      endif
    endforeach
  endforeach
endforeach

if not found_any
  error('MESON_SKIP_TEST: no BLAS/LAPACK libraries available')
endif
