project('object extraction', 'c')

if meson.is_unity()
  message('Skipping extraction test because this is a Unity build.')
else
  lib1 = shared_library('somelib', 'src/lib.c')
  lib2 = shared_library('somelib2', 'lib.c')

  obj1 = lib1.extract_objects('src/lib.c')
  obj2 = lib2.extract_objects(['lib.c'])

  e1 = executable('main 1', 'main.c', objects : obj1)
  e2 = executable('main 2', 'main.c', objects : obj2)

  test('extraction test 1', e1)
  test('extraction test 2', e2)
endif
