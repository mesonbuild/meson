project('object extraction', 'c')

lib = shared_library('somelib', ['lib.c', 'src/lib.c'])
# Also tests that the object list is flattened properly
obj = lib.extract_objects(['lib.c', ['src/lib.c']])
exe = executable('main', 'main.c', objects: obj)
test('extraction', exe)
