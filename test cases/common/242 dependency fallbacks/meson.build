project('dependency fallbacks', 'c')

cc = meson.get_compiler('c')

# Use different dependency name for each case to bypass caching

df = dependency_fallbacks('test1')
d = dependency(df, required: false)
assert(not d.found())

df = dependency_fallbacks('test2', 'zlib')
d = dependency(df)
assert(d.found())

df = dependency_fallbacks('test3')
df.has_function(cc, 'donotexist')
d = dependency(df, required: false)
assert(not d.found())

df = dependency_fallbacks('test4')
df.has_function(cc, 'malloc')
d = dependency(df)
assert(d.found())

df = dependency_fallbacks('test5')
df.find_library(cc, 'z', has_headers: 'notfound.h')
d = dependency(df, required : false)
assert(not d.found())

df = dependency_fallbacks('test6')
df.find_library(cc, 'z', has_headers: 'zlib.h')
d = dependency(df)
assert(d.found())

# foo-1.0 is provided by a wrap
df = dependency_fallbacks('foo-1.0', wraps: false)
d = dependency(df, required: false)
assert(not d.found())

# With wraps it works
df = dependency_fallbacks('foo-1.0')
d = dependency(df)
assert(d.found())

# Now that it is cached, it works even without wraps
df = dependency_fallbacks('foo-1.0', wraps: false)
d = dependency(df)
assert(d.found())

# Subproject foo does not override bar-1.0 but its wrap has the variable name
df = dependency_fallbacks('bar-1.0')
d = dependency(df)
assert(d.found())
