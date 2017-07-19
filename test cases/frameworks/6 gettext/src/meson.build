executable('intlprog', 'intlmain.c', install : true,
  dependencies : meson.get_compiler('c').find_library('intl', required : false))

src_files = i18n.files('intlmain.c', language: 'c', keywords: ['_'])
