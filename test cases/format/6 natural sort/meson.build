# This file is for testing meson format with file sorting enabled

project('default format')

meson_cmd = find_program('meson')
meson_files = {
    'self': files('meson.build'),
    'sort': files('sort_files.meson'),
}
config = files('options.ini')

foreach name, f : meson_files
    test(
        name,
        meson_cmd,
        args: ['format', '--check-only', '--configuration', config, f],
    )
endforeach
