project('C# library', 'cs')

l = shared_library('helper', 'helper.cs', install : true)
e = executable('prog', 'prog.cs', link_with : l, install : true)
test('libtest', e)
