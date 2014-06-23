project('rust shared library', 'rust')

l = shared_library('stuff', 'stuff.rs', install : true)
e = executable('prog', 'prog.rs', link_with : l, install : true)
test('linktest', e)
