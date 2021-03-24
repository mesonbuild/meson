project('zigtest-polyglot', 'c', 'zig')

inc = include_directories('include')

lib = library(
  'hello',
  'src/hello.c',
  include_directories : inc,
)

executable(
  'zigtest-polyglot',
  'src/main.zig',
  link_with : lib,
  include_directories : inc,
)

executable(
  'all-in-one',
  'src/hello.c',
  'src/main.zig',
  include_directories : inc,
)

fs = import('fs')

copied = fs.copyfile('src/hello.c', 'copy.c')
executable(
  'generated-c-static-zig',
  'src/main.zig',
  copied,
  include_directories : inc,
)
