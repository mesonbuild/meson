project('test-args-and-depends-in-path', 'c')

subdir('libs')

dl_dep = dependency('dl', required: false)

fs = import('fs')

test_exe = executable('test-exe',
                      c_args: [
                        '-DLIBA=' + fs.name(lib_a.full_path()),
                        '-DLIBB=' + fs.name(lib_b.full_path()),
                      ],
                      sources: ['test.c'],
                      dependencies: [dl_dep])

test ('test', test_exe,
      args: [lib_a],
      depends: [lib_b])
