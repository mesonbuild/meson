project('shared version meta', 'c')

lib = shared_library('mylib', 'libfile.c', version: '1.0.0+master.b88bec0')
exe = executable('prog', 'main.c', link_with: lib)

test('test', exe)
