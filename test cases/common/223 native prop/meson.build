project('get prop')

x = meson.get_external_property('astring')
ref = meson.is_cross_build() ? 'cross' : 'mystring'
assert(x==ref, 'did not get native property string. did you use "meson setup --native-file native.txt"')

x = meson.get_external_property('astring', native: true)
assert(x=='mystring', 'did not get native property with native:true and non-cross build.')

x = meson.get_external_property('astring', 'fallback', native: false)
assert(x==ref, 'did not get get native property with native:false and non-cross build.')


x = meson.get_external_property('notexist', 'fallback')
assert(x=='fallback', 'fallback did not work')

x = meson.get_external_property('notexist', 'fallback', native: true)
assert(x=='fallback', 'fallback native:true did not work')

x = meson.get_external_property('notexist', 'fallback', native: false)
assert(x=='fallback', 'fallback native:false did not work')


x = meson.get_external_property('anarray')
assert(x==['one', 'two'], 'array did not work')