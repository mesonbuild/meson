project('minimal bindgen', 'c', 'rust', meson_version : '>= 1.0.0')

rust = import('rust')

header_rs = rust.bindgen(input : 'header.h', output : 'header.rs')
