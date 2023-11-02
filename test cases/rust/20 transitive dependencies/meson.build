project('transitive dependencies', 'rust', 'c',
  version : '1.0.0',
  meson_version : '>= 1.0.0',
  default_options : ['rust_std=2018'],
)

subdir('liba')
subdir('libb')

main = executable('main', 'main.rs',
  dependencies : [libb_dep],
)

# Since foo-rs is a static library, its dependencies are normally added to
# footest link command. However, since pm is a proc-macro, footest should not
# link with it. In native build this is an harmless overlinking, but in cross
# building foo and pm are for different arch and it would fail to link.
rust = import('rust')
pm = rust.proc_macro('pm', 'proc.rs')
foo = static_library('foo-rs', 'foo.rs',
  rust_abi: 'c',
  link_with: pm,
)
exe = executable('footest', 'foo.c',
  link_with: foo,
)
test('footest', exe)
