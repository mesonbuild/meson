project('rust shared library', 'rust')

l = shared_library('stuff', 'stuff.rs')
e = executable('prog', 'prog.rs', link_with : l)
test('linktest', e)
