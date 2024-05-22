# This file is for testing meson format with default options

project('default format')

meson_cmd = find_program('meson')
meson_files = {
    'self': files('meson.build'),
    'comments': files('crazy_comments.meson'),
    'indentation': files('indentation.meson'),
    'gh13242': files('gh13242.meson'),
}

foreach name, f : meson_files
    test(name, meson_cmd, args: ['format', '--check-only', f])
endforeach
