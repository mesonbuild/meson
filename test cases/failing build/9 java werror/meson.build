project('test', default_options: ['werror=true'])
if meson.backend() != 'ninja'
  error('MESON_SKIP_TEST: Java requires Ninja backend')
endif
if not add_languages('java', required: false)
  error('MESON_SKIP_TEST: Java not found')
endif
jar('prog', 'Test.java')
