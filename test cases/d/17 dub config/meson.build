project('dub-config', ['c', 'd'])

dub_exe = find_program('dub', required : false)
if not dub_exe.found()
    error('MESON_SKIP_TEST: Dub not found')
endif

if meson.get_compiler('d').get_id() == 'gcc'
    error('MESON_SKIP_TEST: can\'t build dependencies with GDC')
endif

tls_dep = dependency('vibe-d:tls',
    method: 'dub',
    configuration: 'notls',
)

http_dep = dependency('vibe-d:http',
    method: 'dub',
    configuration: 'vibe-d:tls/notls',
)

executable('test_tls', 'test.d',
    dependencies: tls_dep,
)

executable('test_http', 'test.d',
    dependencies: http_dep,
)
