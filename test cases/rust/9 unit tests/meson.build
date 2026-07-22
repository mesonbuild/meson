project('rust unit tests', 'rust', meson_version: '>=1.11.0')

t = executable(
  'rust_test',
  ['test.rs'],
  override_options: {'rust_panic': 'none'},
  rust_args : ['--test'],
)

test(
  'rust test (should fail)',
  t,
  protocol : 'rust',
  suite : ['foo'],
  expected_fail : true,
)

test(
  'rust test (should pass)',
  t,
  args : ['--skip', 'test_add_intentional_fail'],
  protocol : 'rust',
  suite : ['foo'],
)


test(
  'rust test (should skip)',
  t,
  args : ['--skip', 'test_add'],
  protocol : 'rust',
  suite : ['foo'],
)

rust = import('rust')

rustdoc = find_program('rustdoc', required: false)
if rustdoc.found()
  doclib = static_library('rust_doc_lib', ['doctest1.rs'], build_by_default : false)
  rust.doctest('rust doctests', doclib,
    protocol : 'rust',
    suite : ['doctests'],
  )

  # abort not valid for shared libraries:
  #   error: the linked panic runtime `panic_unwind` is not compiled with this crate's panic strategy `abort`
  if get_option('rust_panic') != 'abort'
    doclib = shared_library('rust_doc_lib', ['doctest1.rs'], build_by_default : false)
    rust.doctest('rust shared doctests', doclib,
      protocol : 'rust',
      suite : ['doctests'],
    )
  endif
endif

exe = executable('rust_exe', ['test2.rs', 'test.rs'], build_by_default : false)

rust.test('rust_test_from_exe', exe, expected_fail : true)

lib = static_library('rust_static', ['test.rs'], build_by_default : false, rust_abi: 'c')
rust.test('rust_test_from_static', lib, args: ['--skip', 'test_add_intentional_fail'])

lib = shared_library('rust_shared', ['test.rs'], build_by_default : false)
rust.test('rust_test_from_shared', lib, args: ['--skip', 'test_add_intentional_fail'])

if get_option('rust_panic') != 'abort'
  # abort not valid when linking into tests:
  #   error: the crate `helper` requires panic strategy `abort` which is incompatible with this crate's strategy of `unwind`
  helper = static_library('helper', 'helper.rs')
  lib = static_library('rust_link_with', 'test3.rs', build_by_default : false)
  rust.test('rust_test_link_with', lib, link_with : helper, rust_args : ['--cfg', 'broken="false"'])
endif
