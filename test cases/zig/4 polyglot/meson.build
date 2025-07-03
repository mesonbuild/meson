project('zigtest-polyglot', 'c', 'zig')

lib = library('hello', 'src/hello.c')
executable('zigtest-polyglot', 'src/main.zig',
    link_with: lib
)

executable('all-in-one', 'src/hello.c', 'src/main.zig')

fs = import('fs')

copied = fs.copyfile('src/hello.c', 'copy.c')
executable('generated-c-static-zig', 'src/main.zig', copied)
