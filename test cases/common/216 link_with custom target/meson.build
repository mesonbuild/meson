project('link_with custom target', ['c'])

lib_generator = find_program('lib_generator.py')

cc = meson.get_compiler('c').cmd_array().get(-1)

libfoo_target = custom_target(
    'libfoo',
    input: ['foo.c'],
    output: ['libfoo.a'],
    command: [lib_generator, cc, '@INPUT@', '@OUTPUT@']
)

libfoo = declare_dependency(
    link_with: libfoo_target,
)

executable('demo', ['demo.c'], dependencies: [libfoo])
