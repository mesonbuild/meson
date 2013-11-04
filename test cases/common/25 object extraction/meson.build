project('object extraction', 'c')

lib = shared_library('somelib', 'lib.c')
obj = lib.extract_objects('lib.c')

e = executable('main', 'main.c', objects : obj)
test('extraction test', e)
