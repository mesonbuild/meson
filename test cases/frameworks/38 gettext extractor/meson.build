project(
    'gettext extractor',
    'c',
    default_options: {'default_library': 'static'},
    meson_version: '1.7.0',
)

i18n = import('i18n')
xgettext = i18n.find_xgettext(
    args: ['-ktr', '--add-comments=TRANSLATOR:', '--from-code=UTF-8'],
    required: false,
)

if not xgettext.found()
    error('MESON_SKIP_TEST xgettext command not found')
endif

subdir('src')
