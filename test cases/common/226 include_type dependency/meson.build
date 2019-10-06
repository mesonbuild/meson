project(
  'dependency include_type',
  ['c', 'cpp'],
)

dep = dependency('zlib', method: 'pkg-config', required : false)
if not dep.found()
  error('MESON_SKIP_TEST zlib was not found')
endif

assert(dep.include_type() == 'preserve', 'include_type must default to "preserve"')

dep_sys = dep.as_system()
assert(dep_sys.include_type() == 'system', 'as_system must return a system dep')

dep2 = dependency('zlib', method: 'pkg-config', include_type : 'system')
assert(dep2.include_type() == 'system', 'include_type must be true when set')

dep2_sys = dep2.as_system('non-system')
assert(dep2_sys.include_type() == 'non-system', 'as_system must set include_type correctly')

sp = subproject('subDep')
sp_dep = sp.get_variable('subDep_dep')
assert(sp_dep.include_type() == 'preserve', 'default is preserve')

sp_dep_sys = sp_dep.as_system('system')
assert(sp_dep_sys.include_type() == 'system', 'changing include_type works')
assert(sp_dep.include_type() == 'preserve', 'as_system must not mutate the original object')
