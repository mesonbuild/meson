project('boosttest', 'cpp')

# We want to have multiple separate configurations of Boost
# within one project. The need to be independent of each other.
# Use one without a library dependency and one with it.

nolinkdep = dependency('boost', modules: 'utility')
linkdep = dependency('boost', modules : ['thread', 'system'])

nolinkexe = executable('nolinkedexe', 'nolinkexe.cc', deps : nolinkdep)
linkexe = executable('linkedexe', 'linkexe.cc', deps : linkdep)

test('Boost nolinktext', nolinkexe)
test('Boost linktext', linkexe)
