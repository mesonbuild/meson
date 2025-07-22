project('subproject', 'c')
assert(get_option('bar') == true)
assert(get_option('werror') == true)
assert(get_option('from_toplevel') == true)

# b_lto is only initialized if used, see test "common/40 options"
cc = meson.get_compiler('c')
if cc.get_id() in ['gcc', 'clang', 'clang-cl']
  assert(get_option('b_lto') == true)
endif

subproject('sub2')
