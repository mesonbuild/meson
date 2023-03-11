project('override compiler')

if not find_program('gcc', required: false).found()
  error('MESON_SKIP_TEST: This test needs gcc program')
endif

meson.override_find_program('c', find_program('my-gcc-wrapper.py'))
add_languages('c')

executable('app', 'main.c')
