project('rust and c polyglot executable', 'c', 'rust')

if host_machine.system() == 'darwin'
  error('MESON_SKIP_TEST: doesnt work right on macos, please fix!')
endif

l = shared_library('stuff', 'stuff.rs', rust_crate_type: 'cdylib', install : true)
e = executable('prog', 'prog.c', link_with : l, install : true)
test('polyglottest', e)
