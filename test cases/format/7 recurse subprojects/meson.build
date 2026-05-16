project('format')

python = import('python')
meson_cmd = [python.find_installation(), find_program('meson').full_path()]
file_compare = find_program(files('compare_format_diff.py'))

test(
    'recurse subprojects',
    file_compare,
    args: meson_cmd,
    workdir: meson.project_source_root(),
)

subproject('find-me')
