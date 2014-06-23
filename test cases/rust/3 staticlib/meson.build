project('rust static library', 'rust')

l = static_library('stuff', 'stuff.rs', install : true)
e = executable('prog', 'prog.rs', link_with : l, install : true)
test('linktest', e)
