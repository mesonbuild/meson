project('dependency fallbacks', 'c')

cc = meson.get_compiler('c')

# Use different dependency name for each case to bypass caching

fallbacks = dependency_fallbacks()
fallbacks.dependency('')
d = dependency('test1', fallbacks, required: false)
assert(not d.found(), 'Should not be found')

fallbacks = dependency_fallbacks()
fallbacks.dependency('zlib')
d = dependency('test2', fallbacks)
assert(d.found(), 'Should be found')

fallbacks = dependency_fallbacks()
fallbacks.has_function(cc, 'donotexist')
d = dependency('test3', fallbacks, required: false)
assert(not d.found(), 'Should not be found')

fallbacks = dependency_fallbacks()
fallbacks.has_function(cc, 'malloc')
d = dependency('test4', fallbacks)
assert(d.found(), 'Should be found')

fallbacks = dependency_fallbacks()
fallbacks.find_library(cc, 'z', has_headers: 'notfound.h')
d = dependency('test5', fallbacks, required : false)
assert(not d.found(), 'Should not be found')

fallbacks = dependency_fallbacks()
fallbacks.find_library(cc, 'z', has_headers: 'zlib.h')
d = dependency('test6', fallbacks)
assert(d.found(), 'Should be found')

# Real-life case
fallbacks = dependency_fallbacks()
fallbacks.dependency('libxml2')
fallbacks.dependency('libxml-2.0')
fallbacks.find_library(cc, 'xml2', has_headers: 'libxml/tree.h')
fallbacks.find_library(cc, 'libxml2', has_headers: 'libxml/tree.h')
fallbacks.subproject('xml2', variable: 'xml2_dep')
d = dependency('xml2', fallbacks)
assert(d.found(), 'Should be found')
