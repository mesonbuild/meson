project('static rust and c polyglot executable', 'c', 'rust')

deps = [
  meson.get_compiler('c').find_library('dl'),
  dependency('threads'),
]

l = static_library('stuff', 'stuff.rs', rust_crate_type : 'staticlib', install : true)
e = executable('prog', 'prog.c', dependencies: deps, link_with : l, install : true)
test('polyglottest', e)
