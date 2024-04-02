# test to_list() for include_directories defined in the parent meson.build file
source_dir = meson.project_source_root()
build_dir = meson.project_build_root()

expected = [source_dir / '.', build_dir / '.']
message('actual: @0@'.format(inc.to_list()))
message('expected: @0@'.format(expected))

# Use fs.as_posix() because / operator replaces \ with / in the path, but
# full_path() method is not doing that. This is a pretty inconsistent across all
# Meson APIs.
fs = import('fs')
assert(fs.as_posix('@0@'.format(inc.to_list())) == '@0@'.format(expected))

# test include directories
t = executable(
  'main',
  ['main.c', 'rone.c'],
  include_directories : inc,
  implicit_include_directories : false,
)
