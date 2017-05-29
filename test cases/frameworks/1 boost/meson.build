project('boosttest', 'cpp',
  default_options : ['cpp_std=c++11'])

# We want to have multiple separate configurations of Boost
# within one project. The need to be independent of each other.
# Use one without a library dependency and one with it.

nolinkdep = dependency('boost', modules: 'utility')
linkdep = dependency('boost', modules : ['thread', 'system'])
staticdep = dependency('boost', modules : ['thread', 'system'], static : true)
testdep = dependency('boost', modules : 'test')
nomoddep = dependency('boost')

nolinkexe = executable('nolinkedexe', 'nolinkexe.cc', dependencies : nolinkdep)
linkexe = executable('linkedexe', 'linkexe.cc', dependencies : linkdep)
staticexe = executable('staticlinkedexe', 'linkexe.cc', dependencies : staticdep)
unitexe = executable('utf', 'unit_test.cpp', dependencies: testdep)
nomodexe = executable('nomod', 'nomod.cpp', dependencies : nomoddep)

test('Boost nolinktest', nolinkexe)
test('Boost linktest', linkexe)
test('Boost statictest', staticexe)
test('Boost UTF test', unitexe)
test('Boost nomod', nomodexe)
