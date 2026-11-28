project('bindgen subproject', 'c', meson_version: '>= 1.4.0')

subproject('bindgen')
rust = import('rust')
bindings = rust.bindgen(
  input: 'header.h',
  output: 'header.rs',
  bindgen_version: '>= 0.71',
)
