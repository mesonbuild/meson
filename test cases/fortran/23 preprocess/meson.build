project('preprocess', 'fortran', meson_version: '>1.3.2')

fc = meson.get_compiler('fortran')

pp_files = fc.preprocess(
    'main.f90',
    compile_args: ['-DCORRECT=true'],
    output: '@PLAINNAME@')

t = executable('foo', pp_files)

test('check_result', t)
