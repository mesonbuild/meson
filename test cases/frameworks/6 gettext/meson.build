project('gettext example', 'c')

gettext = find_program('gettext', required: false)
if not gettext.found()
  error('MESON_SKIP_TEST gettext not found.')
endif

if not meson.get_compiler('c').has_header('libintl.h')
  error('MESON_SKIP_TEST libintl.h not found.')
endif

i18n = import('i18n')

subdir('po')
subdir('src')
subdir('data')
