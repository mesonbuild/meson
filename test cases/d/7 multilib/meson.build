project('D Multiple Versioned Shared Libraries', 'd')

if meson.get_compiler('d').get_id() == 'gcc'
  error('MESON_SKIP_TEST: GDC can not build shared libraries (2016)')
endif

ldyn1 = shared_library('say1',
    'say1.d',
    install: true,
    version : '1.2.3',
    soversion : '0'
)
ldyn2 = shared_library('say2',
    'say2.d',
    install: true,
    version : '1.2.4',
    soversion : '1'
)

ed = executable('app_d', 'app.d', link_with: [ldyn1, ldyn2], install: true)
test('multilink_test', ed)
