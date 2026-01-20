project('rust shared library', 'rust', 'c')

subdir('cdylib')

s = static_library('static', 'value.c')

# Test link_depends with a custom_target for Rust shared library.
# rustc provides a version script of its own; GNU ld does not
# support multiple version scripts, lld does
if host_machine.system() == 'linux' and find_program('lld', required : false).found()
  ct_map = import('fs').copyfile('stuff.map', 'stuff-ct.map')
  vflag = ['-fuse-ld=lld', '-Wl,--version-script,' + ct_map.full_path()]
  rustl = shared_library('stuff', 'stuff.rs', link_whole : s, install : true,
                     link_args : vflag, link_depends : ct_map)
else
  rustl = shared_library('stuff', 'stuff.rs', link_whole : s, install : true)
endif
e = executable('prog', 'prog.rs', link_with : [rustl, cl], install : true)

if build_machine.system() == 'windows'
  rustup = find_program('rustup')
  test('linktest', rustup,
       args: ['run', 'stable', e])
else
  test('linktest', e)
endif
