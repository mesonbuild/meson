project(
  'meson-runtime', ['c'],
  version: '0.0.1',
  meson_version : '>=0.58.0',
  default_options : [
    'b_lto=true',
    'default_library=static',
    'warning_level=3',
    'werror=true',
    'debug=false',
    'optimization=s',

    'fuse:werror=false',
    'fuse3:werror=false',
    'squashfuse:werror=false',
    'zstd:werror=false',
    'liblzma:werror=false',
    'liblzma:warning_level=0',
    'lz4:warning_level=0',
    'zlib:warning_level=0',
    'zstd:warning_level=0',
    'zstd:bin_programs=false',
  ],
)

add_project_link_arguments('-static', language: 'c')
add_project_arguments('-DFUSE_USE_VERSION=26', language: 'c')

dd_prog      = find_program('dd')
objcopy_prog = find_program('objcopy')

libruntime_sp  = subproject('libruntime')
libruntime_dep = libruntime_sp.get_variable('libruntime_dep')
patcher_prog   = libruntime_sp.get_variable('patcher_prog')

# Build the unpatched executable
conf_data = configuration_data()
conf_data.set_quoted('RUNTIME_VERSION', meson.project_version())
conf_data.set_quoted('BUILD_ID', run_command(find_program('genid.py')).stdout().strip())
conf_data.set10('VERBOSE', get_option('debug'))
configure_file(output: 'runtime-config.h', configuration: conf_data)

runtime_raw = executable(
    'runtime_raw', ['main.c'],
    dependencies: [libruntime_dep],
)

# Patch the executable
custom_target(
    'runtime',
    input:       [runtime_raw],
    output:      ['runtime'],
    install:     true,
    install_dir: get_option('bindir'),
    command: [
        patcher_prog,
        '-i', '@INPUT@',
        '-o', '@OUTPUT@',
        '-p', '@PRIVATE_DIR@',
        # '-e',
        '--dd', dd_prog,
        '--objcopy', objcopy_prog,
    ],
)
