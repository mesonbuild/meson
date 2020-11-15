project('zigtest-shared-lib', 'zig', version: '0.1.0')

lib = shared_library('hello', 'lib/hello.zig')
executable('zigtest-shared-lib', 'src/main.zig', link_with: lib)
