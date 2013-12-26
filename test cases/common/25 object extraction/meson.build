project('object extraction', 'c')

if meson.is_unity()
  message('Skipping extraction test because this is a Unity build.')
else
  lib = shared_library('somelib', 'lib.c')
  obj = lib.extract_objects('lib.c')

  e = executable('main', 'main.c', objects : obj)
  test('extraction test', e)
endif
