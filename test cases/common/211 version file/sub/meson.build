mapfile = 'foo' + suffix

l = shared_library('foo', '../bob.c', symbol_export_file: mapfile)
e = executable('prog-foo', '../prog.c', link_with : l)
test('core', e)
