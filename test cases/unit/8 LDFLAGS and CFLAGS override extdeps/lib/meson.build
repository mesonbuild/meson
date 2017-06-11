cc = meson.get_compiler('c').cmd_array()
zlib_o = configure_file(input : 'zlib.c',
                        output : 'zlib.o',
                        command : cc + ['-c', '-fPIC', '@INPUT@', '-o', '@OUTPUT@'])
zlib_so = configure_file(input : zlib_o,
                         output : 'libz.so',
                         command : cc + ['@INPUT@', '-shared', '-fPIC', '-o', '@OUTPUT@'])
libdir = meson.current_build_dir()
