project('static link order', 'c')

if host_machine.system() in ['windows', 'cygwin']
  error('MESON_SKIP_TEST: symbol interposition is not available')
endif

interpose = static_library('interpose', 'interpose.c')
link_with = shared_library('link_with', 'link_with.c')

# libmylib depends on libinterpose. liblink_with is a shared library that
# defines the same symbol as libinterpose.  libinterpose must come before
# liblink_with, so that the executables use the symbol from libinterpose.
mylib = static_library('mylib', 'mylib.c', link_with: interpose)
exe = executable('prog-separate', 'main.c', link_with: [mylib, link_with])
test('interpose.a as separate linked file', exe)

# In this case, libmylib includes libinterpose directly.
mylib_install = static_library('mylib_install', 'mylib.c', install: true, link_with: interpose)
exe = executable('prog-internallib', 'main.c', link_with: [mylib_install, link_with])
test('interpose.a as internal library', exe)
