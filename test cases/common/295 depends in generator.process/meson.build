project('test_depends_in_generator_process', 'c')

generate_main_py = find_program('generate_main.py')
generate_config_py = find_program('generate_config.py')

main_generator = generator(
    generate_main_py,
    arguments: ['@INPUT@', '@OUTPUT@'],
    output: '@BASENAME@' + '.c',
)

main_template = files('main.template')
main_config_ini = files('main.config.ini')

my_config_h = custom_target(
    'main.config.h',
    output: 'main.config.h',
    input: main_config_ini,
    command: [ generate_config_py, '@INPUT@', '@OUTPUT@' ],
)

my_executable = executable(
    'myexecutable',
    sources: main_generator.process(
        main_template,
        depends: my_config_h,
    )
)

test('depends in generator.process', my_executable)
