project('test', default_options: ['werror=true'])
if meson.backend() != 'ninja'
  error('MESON_SKIP_TEST: C# requires Ninja backend')
endif
if not add_languages('cs', required: false)
  error('MESON_SKIP_TEST: C# not found')
endif
executable('prog', 'test.cs')
