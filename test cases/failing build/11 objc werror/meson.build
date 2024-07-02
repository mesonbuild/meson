project('test', default_options: ['werror=true'])
if not add_languages('objc', required: false)
  error('MESON_SKIP_TEST: Objective C not found')
endif
executable('prog', 'test.m')
