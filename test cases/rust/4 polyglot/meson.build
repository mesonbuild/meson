project('rust and c polyglot executable', 'c', 'rust')

l = library('stuff', 'stuff.rs', rust_crate_type: 'cdylib', install : true)
e = executable('prog', 'prog.c', link_with : l, install : true)
test('polyglottest', e)
