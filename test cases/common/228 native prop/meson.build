project('get native prop')

x = meson.get_native_property('astring')
assert(x=='mystring', 'did not get native property string. did you use "meson setup --native-file native.txt"')

x = meson.get_native_property('notexist', 'fallback')
assert(x=='fallback', 'fallback did not work')

x = meson.get_native_property('anarray')
assert(x==['one', 'two'], 'array did not work')