project('meson system dependency', 'c', meson_version: '>=1.7.0')

cc = meson.get_compiler('c')

# We could check if dependency('atomic') actually finds something when
# we 'know' it exists (MESON_SKIP_TEST) but that's likely to be brittle,
# so don't bother (for now, at least).
atomic = dependency('atomic', required : false)

# If the dependency provider says it found something, make sure it can
# be linked against (https://github.com/mesonbuild/meson/issues/14946).
dependencies = [
  atomic
]

exe = executable(
  'a',
  'a.c',
  dependencies : dependencies,
  install : false,
)

test('basic', exe)
