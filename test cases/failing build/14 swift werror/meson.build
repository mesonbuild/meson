project('test', default_options: ['werror=true'])
if not add_languages('swift', required: false)
  error('MESON_SKIP_TEST: Swift not found')
endif
executable('prog', 'test.swift')
