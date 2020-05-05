project('CMake dependency include dirs', ['c', 'cpp'])

if not find_program('cmake', required: false).found()
  error('MESON_SKIP_TEST cmake binary not available.')
endif

dep = dependency('MythicalDependencyInOpt', required: true, method: 'cmake', cmake_module_path: 'cmake')
assert(dep.get_include_paths() == ['/opt/local/include', '/foo/bar/baz'], 'Dependency get_include_paths failed.')
