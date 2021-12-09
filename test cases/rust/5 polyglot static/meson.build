project('static rust and c polyglot executable', 'c', 'rust')

deps = [
  meson.get_compiler('c').find_library('dl', required: false),
  meson.get_compiler('c').find_library('m', required: false),
  dependency('threads'),
]

extra_winlibs = meson.get_compiler('c').get_id() in ['msvc', 'clang-cl'] ? ['userenv.lib', 'ws2_32.lib', 'bcrypt.lib'] : []

l = static_library('stuff', 'stuff.rs', rust_crate_type : 'staticlib', install : true)
e = executable('prog', 'prog.c',
               dependencies: deps,
               link_with : l,
               link_args: extra_winlibs,
               install : true)
test('polyglottest', e)
