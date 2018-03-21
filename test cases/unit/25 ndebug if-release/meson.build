project('ndebug enabled', 'c')

if meson.get_compiler('c').get_id() == 'msvc'
  error('MESON_SKIP_TEST b_ndebug is not supported on Visual Studio')
endif

executable('main', 'main.c')
