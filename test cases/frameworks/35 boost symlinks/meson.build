project('boosttestsymlinks', 'cpp')

bm = build_machine.system()

if bm == 'windows' or bm == 'cygwin'
  error('MESON_SKIP_TEST: Windows and symlinks do not mix.')
endif

dep = dependency('boost', modules : ['regex', 'python'], required: false)

assert(dep.found(), 'expected to find a fake version of boost')
assert(dep.version() == '0.3.0', 'expected to find version 0.3.0')
