project('format')

fs = import('fs')

meson_cmd = find_program('meson')
file_compare = find_program(files('file_compare.py'))
config = get_option('fmt_config')

source = files('source.meson')
config_file = files(config + '.ini')
expected = files(config + '.expected.meson')

transform = custom_target(
    input: [config_file, source],
    output: 'transformed.meson',
    command: [
        meson_cmd,
        'format',
        '--output', '@OUTPUT@',
        '--configuration', '@INPUT@',
    ],
)


test(
    'transform',
    file_compare,
    args: [transform, expected],
)
