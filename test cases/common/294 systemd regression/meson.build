# regression test - meson puts the directories in the reversed order for
# "is_system: true", which is bad but happens for historical reasons.

# SPDX-License-Identifier: LGPL-2.1-or-later

project('test', 'c', meson_version: '>=0.62.0', version: '1.0')

if host_machine.system() != 'linux'
  error('MESON_SKIP_TEST: systemd include ordering regression test needs Linux')
endif

conf = configuration_data()
config_h = configure_file(output : 'config.h', configuration : conf)
userspace = declare_dependency(compile_args : ['-include', 'config.h'])

system_includes = [
        include_directories(
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


# second testcase, with separate include_directories

system_includes = [
        include_directories('uapi', is_system : true),
        include_directories('override', is_system : true),
]

static_library(
        'c-wrapper2',
        files('keyctl.c'),
        include_directories : system_includes,
        implicit_include_directories : false,
        dependencies : [userspace],
        c_args : ['-fvisibility=default'],
        build_by_default : true)
