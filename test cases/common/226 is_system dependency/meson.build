project(
  'dependency is_system',
  ['c', 'cpp'],
)

dep = dependency('zlib', method: 'pkg-config', required : false)
if not dep.found()
  error('MESON_SKIP_TEST zlib was not found')
endif

assert(dep.is_system() == false, 'is_system must default to false')

dep_sys = dep.as_system()
assert(dep_sys.is_system() == true, 'as_system must default to true')

dep2 = dependency('zlib', method: 'pkg-config', is_system : true)
assert(dep2.is_system() == true, 'is_system must be true when set')

dep2_sys = dep2.as_system(false)
assert(dep2_sys.is_system() == false, 'as_system must set is_system correctly')
