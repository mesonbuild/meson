# this test case can be deleted if support for unversioned python libs is removed

project('boosttest', 'cpp')

dep = dependency('boost', modules : ['python','numpy'], required: false)

assert(dep.found(), 'expected to find a fake version of boost')
assert(dep.version() == '0.1.0', 'expected to find version 0.1.0')
