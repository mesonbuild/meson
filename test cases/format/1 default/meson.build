# This file is for testing meson format with default options

project('default format')

meson_cmd = find_program('meson')
meson_files = {
    'self': files('meson.build'),
    'comments': files('crazy_comments.meson'),
    'indentation': files('indentation.meson'),
    'gh13242': files('gh13242.meson'),
}

# Ensure empty function are formatted correctly on long lines
a = '@0@@1@@2@@3@@4@'.format('one', 'two', 'three', 'four', 'five').strip().strip()

_opt = get_option('opt') \
    .disable_if(
        true,
        error_message: 'This is an error message because opt can\'t be enabled',
    ) \
    .enable_if(
        false,
        error_message: 'This is an error message because opt can\'t be disabled',
    )

foreach name, f : meson_files
    test(name, meson_cmd, args: ['format', '--check-only', f])
endforeach
