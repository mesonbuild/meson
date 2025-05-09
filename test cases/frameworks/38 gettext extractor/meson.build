project(
    'gettext extractor',
    'c',
    default_options: {'default_library': 'static'},
    meson_version: '>=1.8.0',
)

if not find_program('xgettext', required: false).found()
    error('MESON_SKIP_TEST xgettext command not found')
endif

if host_machine.system() == 'darwin'
    error('MESON_SKIP_TEST test is unstable on macOS for unknown reasons')
endif

i18n = import('i18n')
xgettext_args = ['-ktr', '--add-comments=TRANSLATOR:', '--from-code=UTF-8']

subdir('src')
