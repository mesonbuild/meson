project('declare dependency', 'c')

subdir('entity')

exe = executable('dep_user', 'main.c',
  dependencies : entity_dep,
  install: true)

test('dep', exe)

meson.install_dependency_manifests()
