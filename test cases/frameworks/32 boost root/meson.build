project('boosttest', 'cpp')

dep = dependency('boost', required: false)
assert(dep.found(), 'expected to find a fake version of boost')
assert(dep.version() == '0.0.1', 'expected to find version 0.0.1')
