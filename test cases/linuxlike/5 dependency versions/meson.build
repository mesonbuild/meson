project('dep versions', 'c')

# Find external dependency without version
zlib = dependency('zlib')
# Find external dependency with version
zlibver = dependency('zlib', version : '>1.0')
assert(zlib.version() == zlibver.version(), 'zlib versions did not match!')
# Find external dependency with conflicting version
assert(zlib.type_name() == 'pkgconfig', 'zlib should be of type "pkgconfig" not ' + zlib.type_name())
zlibver = dependency('zlib', version : '<1.0', required : false)
assert(zlibver.found() == false, 'zlib <1.0 should not be found!')

# Test https://github.com/mesonbuild/meson/pull/610
dependency('somebrokenlib', version : '>=2.0', required : false)
dependency('somebrokenlib', version : '>=1.0', required : false)

# Find internal dependency without version
somelibver = dependency('somelib',
  fallback : ['somelibnover', 'some_dep'])
assert(somelibver.type_name() == 'internal', 'somelibver should be of type "internal", not ' + somelibver.type_name())
# Find an internal dependency again with the same name and a specific version
somelib = dependency('somelib',
  version : '== 0.1',
  fallback : ['somelib', 'some_dep'])
# Find an internal dependency again with the same name and incompatible version
somelibver = dependency('somelib',
  version : '>= 0.3',
  fallback : ['somelibver', 'some_dep'])
# Find somelib again, but with a fallback that will fail
somelibfail = dependency('somelib',
  version : '>= 0.2',
  required : false,
  fallback : ['somelibfail', 'some_dep'])
assert(somelibfail.found() == false, 'somelibfail found via wrong fallback')

fakezlib_dep = dependency('zlib',
  fallback : ['somelib', 'fakezlib_dep'])
assert(fakezlib_dep.type_name() == 'internal', 'fakezlib_dep should be of type "internal", not ' + fakezlib_dep.type_name())
