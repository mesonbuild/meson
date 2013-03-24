project('boosttest', 'cxx')

# One test case for a Boost module that is
# header only and one test case for a module that
# requires linking with a shared library.

nolinkdep = find_dep('boost', modules : 'utility', required : true)
linkdep = find_dep('boost', modules : 'thread', required : true)

nolinkexe = executable('nolinkexe', 'nolinkexe.cc', dep : nolinkdep)
linkexe = executable('linkedexe', 'linkexe.cc', dep : linkdep)

add_test('nolinktest', nolinkexe)
add_test('linktext', linkexe)
