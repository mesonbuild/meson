project('minimal bindgen', 'c', meson_version : '>= 1.0.0')

if get_option('add_rust_language')
  add_languages('rust', required: true, native: false)
  add_languages('rust', required: true, native: true)
endif

rust = import('rust')
header_rs = rust.bindgen(input : 'header.h', output : 'header.rs')
