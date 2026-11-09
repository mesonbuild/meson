project('bindgen', 'c', version: '0.71.0')

# A controlled stand-in for bindgen: it must only run at build time.
bindgen = executable('bindgen', 'bindgen.c', native: true, build_by_default: false)
meson.override_find_program('bindgen', bindgen)
