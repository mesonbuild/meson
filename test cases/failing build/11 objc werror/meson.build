project('test', default_options: ['werror=true'])
if not add_languages('objc', required: false)
  error('MESON_SKIP_TEST: Objective C not found')
endif
if get_option('backend').startswith('vs')
  error('MESON_SKIP_TEST: objcpp is not supported by vs backend')
endif
executable('prog', 'test.m')
