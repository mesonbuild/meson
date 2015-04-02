project('object extraction', 'c')

if meson.is_unity()
  message('Skipping extraction test because this is a Unity build.')
else
  lib = shared_library('somelib', 'lib.c')

  obj1 = lib.extract_objects('lib.c')
  obj2 = lib.extract_objects(['lib.c'])

  e1 = executable('main 1', 'main.c', objects : obj1)
  e2 = executable('main 2', 'main.c', objects : obj2)

  test('extraction test 1', e1)
  test('extraction test 2', e2)
endif
