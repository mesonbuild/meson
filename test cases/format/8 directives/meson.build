project('format directives')

python = import('python')
meson_cmd = find_program('meson')
file_compare = find_program(files('file_compare.py'))
check_recurse = find_program(files('check_recurse.py'))

foreach name : ['nested', 'strings', 'unpaired', 'multiple', 'muon']
    expected = files(name + '.expected.meson')
    transform = custom_target(
        input: files(name + '.meson'),
        output: name + '.transformed.meson',
        command: [meson_cmd, 'format', '--output', '@OUTPUT@', '@INPUT@'],
    )
    test(name, file_compare, args: [transform, expected])
    test(
        name + ' idempotent',
        meson_cmd,
        args: ['format', '--check-only', expected],
    )
endforeach

# formatting disabled in recurse/meson.build must not apply to recurse/sub/meson.build
test(
    'recurse',
    check_recurse,
    args: [
        files('recurse.expected.diff'),
        python.find_installation(),
        meson_cmd.full_path(),
    ],
    workdir: meson.current_source_dir(),
)
