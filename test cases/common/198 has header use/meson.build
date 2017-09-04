project('has header use', 'c')

c_compiler = meson.get_compiler('c')

assert(not c_compiler.has_header('header_cannotbeused.h', use : true, args : '-I' + meson.source_root()), 'non-usable header is usable')
assert(c_compiler.has_header('header_canbeused.h', use : true, args : '-I' + meson.source_root()), 'usable header is not usable')
