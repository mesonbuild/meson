project('boosttest', 'cpp',
  default_options : ['cpp_std=c++11'])

add_project_arguments(['-DBOOST_LOG_DYN_LINK'],
  language : 'cpp'
)

dep = dependency('boost', required: false)
if not dep.found()
  error('MESON_SKIP_TEST boost not found.')
endif

# We want to have multiple separate configurations of Boost
# within one project. The need to be independent of each other.
# Use one without a library dependency and one with it.

linkdep = dependency('boost', modules : ['thread', 'system', 'test'])
staticdep = dependency('boost', modules : ['thread', 'system'], static : true)
testdep = dependency('boost', modules : ['unit_test_framework'])
nomoddep = dependency('boost')
extralibdep = dependency('boost', modules : ['thread', 'system', 'log_setup', 'log'])

linkexe = executable('linkedexe', 'linkexe.cc', dependencies : linkdep)
staticexe = executable('staticlinkedexe', 'linkexe.cc', dependencies : staticdep)
unitexe = executable('utf', 'unit_test.cpp', dependencies: testdep)
nomodexe = executable('nomod', 'nomod.cpp', dependencies : nomoddep)
extralibexe = executable('extralibexe', 'extralib.cpp', dependencies : extralibdep)

test('Boost linktest', linkexe)
test('Boost statictest', staticexe)
test('Boost UTF test', unitexe)
test('Boost nomod', nomodexe)
test('Boost extralib test', extralibexe)

subdir('partial_dep')
