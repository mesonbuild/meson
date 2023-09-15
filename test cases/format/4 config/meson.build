# This file is for testing meson format with custom options

project('default format')

meson_cmd = find_program('meson')
meson_files = {
  'self' : files('meson.build'),
  'comments' : files('crazy_comments.meson'),
  'indentation' : files('indentation.meson'),
}

foreach name, f : meson_files
  test(
    name,
    meson_cmd,
    args : [ 'format', '--configuration', files('options.ini'), '--check-only', f ],
  )
endforeach
