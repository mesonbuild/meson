project('boosttest', 'cxx')

# We want to have multiple separate configurations of Boost
# within one project. The need to be independent of each other.
# Use one without a library dependency and one with it.

nolinkdep = find_dep('boost', modules: 'utility')
linkdep = find_dep('boost', modules : 'thread')

nolinkexe = executable('nolinkedexe', 'nolinkexe.cc', deps : nolinkdep)
linkexe = executable('linkedexe', 'linkexe.cc', deps : linkdep)

add_test('Boost nolinktext', nolinkexe)
add_test('Boost linktext', linkexe)
