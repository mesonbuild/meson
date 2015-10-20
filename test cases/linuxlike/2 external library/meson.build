project('external library', 'c')

zlib = find_library('z')

# Verify that link testing works.
linkcode = '''#include<zlib.h>
int main(int argc, char **argv) {
  void *ptr = (void*)(deflate);
  return ptr == 0;
}
'''

nolinkcode='''int nonexisting();
int main(int argc, char **argv) {
  void *ptr = (void*)(nonexisting);
  return ptr == 0;
}
'''
cc = meson.get_compiler('c')
assert(cc.links(linkcode, args : '-lz', name : 'Test link against zlib'), 'Linking test failed.')
assert(not cc.links(nolinkcode, name : 'Failing link'), 'Linking succeeded when it should have failed.')

e = executable('zprog', 'prog.c', dependencies : zlib)
test('libtest', e)
