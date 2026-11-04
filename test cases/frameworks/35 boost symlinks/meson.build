project('boosttestsymlinks', 'cpp')

bm = build_machine.system()

if bm == 'windows' or bm == 'cygwin'
  error('MESON_SKIP_TEST: Windows and symlinks do not mix.')
endif

dep = dependency('boost', modules : ['regex', 'python315'], required: false)

assert(dep.found(), 'expected to find a fake version of boost')
assert(dep.version() == '0.3.0', 'expected to find version 0.3.0')

# everything below this can be removed when support for unversioned boost_python is removed 

major_version = dependency('boost', modules : ['regex', 'python3'], required: false)

assert(major_version.found(), 'expected to find a fake version of boost')
assert(major_version.version() == '0.3.0', 'expected to find version 0.3.0')

no_version = dependency('boost', modules : ['regex', 'python'], required: false)

assert(no_version.found(), 'expected to find a fake version of boost')
assert(no_version.version() == '0.3.0', 'expected to find version 0.3.0')
