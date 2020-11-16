project('object extraction', 'c')

if meson.is_unity()
  message('Skipping extraction test because this is a Unity build.')
else
  lib1 = shared_library('somelib', 'src/lib.c')
  lib2 = shared_library('somelib2', 'lib.c', 'lib2.c')

  obj1 = lib1.extract_objects('src/lib.c')
  obj2 = lib2.extract_objects(['lib.c'])
  obj3 = lib2.extract_objects(files('lib.c'))
  obj4 = lib2.extract_objects(['lib.c', 'lib.c'])

  e1 = executable('main1', 'main.c', objects : obj1)
  e2 = executable('main2', 'main.c', objects : obj2)
  e3 = executable('main3', 'main.c', objects : obj3)
  e4 = executable('main4', 'main.c', objects : obj4)

  test('extraction test 1', e1)
  test('extraction test 2', e2)
  test('extraction test 3', e3)
  test('extraction test 4', e4)
endif
