project('rust apple framework', ['c', 'rust'], meson_version: '>=1.3.0')

if host_machine.system() != 'darwin'
  error('MESON_SKIP_TEST: this test is only for macOS')
endif

foundation = dependency('appleframeworks', modules: 'Foundation')

timelib = static_library('timelib', 'lib.rs', dependencies: foundation, rust_abi: 'rust')
alias_target('timelib', timelib)

exe = executable('main', 'main.rs', link_with: timelib)
test('main', exe)
