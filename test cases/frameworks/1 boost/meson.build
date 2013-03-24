project('boosttest', 'cxx')

# Use a Boost module that requires a shared library.
# Eventually we would like to be able to detect Boost
# multiple times with different library combinations.

linkdep = find_dep('boost', modules : 'thread', required : true)

linkexe = executable('linkedexe', 'linkexe.cc', deps : linkdep)

add_test('Boost linktext', linkexe)
