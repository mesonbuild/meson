project('cargo subproject', 'rust')

if meson.is_cross_build()
  error('MESON_SKIP_TEST: cargo does not support cross compilation yet')
endif

paste_dep = dependency('paste-1-rs')
exe = executable('main', 'main.rs',
  dependencies: paste_dep,
)
test('cargo-test', exe)
