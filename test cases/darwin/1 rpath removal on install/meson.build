project('proj', 'c')

subdir('foo')

bar = library('bar', 'bar.c',
  link_with: foo,
  install: true,
)

bar_internal = static_library('bar-internal', 'bar.c',
  link_with: foo,
)

main = executable('main', 'main.c',
  link_with: bar_internal,
  install: true,
)
