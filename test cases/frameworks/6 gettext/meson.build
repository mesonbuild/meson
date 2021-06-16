project('gettext example', 'c')

gettext = find_program('gettext', required: false)
if not gettext.found()
  error('MESON_SKIP_TEST gettext not found.')
endif

xgettext = find_program('xgettext', required: false)
if not xgettext.found()
  error('MESON_SKIP_TEST xgettext not found.')
endif

intl = dependency('intl', required: false)
if not intl.found()
  error('MESON_SKIP_TEST libintl/gettext functions not found.')
endif

i18n = import('i18n')

subdir('po')
subdir('src')
subdir('data')
subdir('data2')
subdir('generated')
