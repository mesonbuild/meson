project('11 script path', 'c')

if meson.backend() != 'ninja'
  error('MESON_SKIP_TEST: Ninja backend required')
endif

run = find_program('run.py')

gen = find_program('gen')

src = custom_target(
    'src',
    command: [run, gen],
    output: 'x.c',
)

exe = executable('e',
    src,
)
