# SPDX-License-Identifier: LGPL-2.1-or-later

project('test', 'c', meson_version: '>=0.62.0', version: '1.0', default_options: [ 'c_std=gnu17', ])

if host_machine.system() != 'linux'
  error('MESON_SKIP_TEST: systemd include ordering regression test needs Linux')
endif

conf = configuration_data()
config_h = configure_file(output : 'config.h', configuration : conf)
userspace = declare_dependency(compile_args : ['-include', 'config.h'])

system_includes = [
        include_directories(
                # gcc(1) says
                # "Directories specified with -isystem options are scanned in left-to-right order",
                # and meson puts the directories in the reversed order. Hence, a directory with a lower
                # priority must be listed earlier.
                'uapi',
                'override',
                is_system : true,
        ),
]

static_library(
        'c-wrapper',
        files('keyctl.c'),
        include_directories : system_includes,
        implicit_include_directories : false,
        dependencies : [userspace],
        c_args : ['-fvisibility=default'],
        build_by_default : true)
