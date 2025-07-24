project('valaless-vapigen', 'c')

if host_machine.system() == 'cygwin'
  error('MESON_SKIP_TEST Does not work with the Vala currently packaged in cygwin')
endif

gnome = import('gnome')

clib_src = [
  'clib.c',
  'clib.h'
]

clib_lib = shared_library('clib', clib_src)

clib_gir = gnome.generate_gir(clib_lib,
  sources: clib_src,
  namespace: 'Clib',
  nsversion: '0',
  header: 'clib.h',
  symbol_prefix: 'clib'
)

clib_vapi = gnome.generate_vapi('clib', sources: clib_gir[0])

clib_dep = declare_dependency(
  include_directories: include_directories('.'),
  link_with: clib_lib,
  sources: clib_gir,
  dependencies: clib_vapi
)


test('clib-test', executable('clib-test', 'test_clib.c', dependencies: clib_dep))
