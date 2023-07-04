project('static rust and c polyglot executable', 'c', 'rust')

r = static_library('stuff', 'stuff.rs', rust_crate_type : 'staticlib')

# clib is installed static library and stuff is not installed. That means that
# to be usable clib must link_whole stuff. Meson automatically promote to link_whole,
# as it would do with C libraries, but then cannot extract objects from stuff and
# thus should error out.
# FIXME: We should support this use-case in the future.
testcase expect_error('Cannot link_whole a custom or Rust target into a static library')
  l = static_library('clib', 'clib.c', link_with : r, install : true)
endtestcase

l = static_library('clib', 'clib.c', link_with : r)

e = executable('prog', 'prog.c',
               link_with : l,
               install : true)
test('polyglottest', e)
