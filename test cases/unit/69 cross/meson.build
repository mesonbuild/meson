project('crosstest')

add_languages('c', native: true)
if get_option('generate')
    conf_data = configuration_data()
    conf_data.set('system', build_machine.system())
    conf_data.set('cpu', build_machine.cpu())
    conf_data.set('cpu_family', build_machine.cpu_family())
    conf_data.set('endian', build_machine.endian())
    conf_data.set('c_args', '-pedantic')

    configure_file(input: 'crossfile.in',
                output: 'crossfile',
                configuration: conf_data)
    configure_file(input: 'nativefile.in',
                output: 'nativefile',
                configuration: conf_data)
    message('Written native and cross file')

    add_languages('c', native: false)
    assert(get_option('build.c_args') == get_option('c_args'))
else
    assert(meson.is_cross_build(), 'not setup as cross build')
    assert(get_option('build.c_args') == ['-pedantic'])
endif
