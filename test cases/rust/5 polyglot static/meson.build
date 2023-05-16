project('static rust and c polyglot executable', 'c', 'rust')

r = static_library('stuff', 'stuff.rs', rust_crate_type : 'staticlib')
l = static_library('clib', 'clib.c', link_with : r, install : true)
e = executable('prog', 'prog.c',
               link_with : l,
               install : true)
test('polyglottest', e)
