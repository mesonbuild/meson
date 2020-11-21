project('zigtest-static-lib', 'zig')

lib = static_library('hello', 'lib/hello.zig')
executable('zigtest-static-lib', 'src/main.zig', link_with: lib)
