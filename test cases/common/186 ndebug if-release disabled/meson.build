project('ndebug disabled', 'c',
        default_options : [
          'buildtype=release',
          'b_ndebug=if-release',
        ])

if meson.get_compiler('c').get_id() == 'msvc'
  error('MESON_SKIP_TEST b_ndebug is not supported on Visual Studio')
endif

test('exe', executable('main', 'main.c'))
