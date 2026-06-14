# test to_list() for include_directories defined in the parent meson.build file
source_dir = meson.project_source_root()
build_dir = meson.project_build_root()
expected = [source_dir / '.', build_dir / '.']
# Use fs.as_posix() to ensure the results are the same across platforms.
fs = import('fs')
assert(fs.as_posix('@0@'.format(inc.to_list())) == '@0@'.format(expected))

# test include directories
t = executable(
  'main',
  ['main.c', 'rone.c'],
  include_directories : inc,
  implicit_include_directories : false,
)
