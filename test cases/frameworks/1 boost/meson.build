project('boosttest', 'cpp',
  default_options : ['cpp_std=c++11'])

add_project_arguments(['-DBOOST_LOG_DYN_LINK'],
  language : 'cpp'
)

dep = dependency('boost', required: false)
if not dep.found()
  error('MESON_SKIP_TEST boost not found.')
endif

compiler = meson.get_compiler('cpp')
if compiler.has_argument('-permissive')
  # boost 1.64, the version we test against, doesn't work with -permissive
  add_project_arguments('-permissive', language: 'cpp')
endif

# We want to have multiple separate configurations of Boost
# within one project. The need to be independent of each other.
# Use one without a library dependency and one with it.

linkdep = dependency('boost', modules : ['thread', 'system', 'test'])
staticdep = dependency('boost', modules : ['thread', 'system'], static : true)
testdep = dependency('boost', modules : ['unit_test_framework'])
nomoddep = dependency('boost')
extralibdep = dependency('boost', modules : ['thread', 'system', 'log_setup', 'log'])

pymod = import('python')
python2 = pymod.find_installation('python2', required: host_machine.system() == 'linux', disabler: true)
python3 = pymod.find_installation('python3', required: host_machine.system() == 'linux', disabler: true)
python2dep = python2.dependency(required: host_machine.system() == 'linux', disabler: true)
python3dep = python3.dependency(required: host_machine.system() == 'linux', disabler: true)

# compile python 2/3 modules only if we found a corresponding python version
if(python2dep.found() and host_machine.system() == 'linux')
  if(dep.version().version_compare('>=1.67'))
    # if we have a new version of boost, we need to construct the module name based
    # on the installed version of python (and hope that they match the version boost
    # was compiled against)
    py2version_string = ''.join(python2dep.version().split('.'))
    bpython2dep = dependency('boost', modules : ['python' + py2version_string])
  else
    # if we have an older version of boost, we need to use the old module names
    bpython2dep = dependency('boost', modules : ['python'])
  endif

  if not (bpython2dep.found())
    bpython2dep = disabler()
  endif
else
  python2dep = disabler()
  bpython2dep = disabler()
endif

if(python3dep.found() and host_machine.system() == 'linux')
  if(dep.version().version_compare('>=1.67'))
    py3version_string = ''.join(python3dep.version().split('.'))
    bpython3dep = dependency('boost', modules : ['python' + py3version_string])
  else
    bpython3dep = dependency('boost', modules : ['python3'])
  endif

  if not (bpython3dep.found())
    bpython3dep = disabler()
  endif
else
  python3dep = disabler()
  bpython3dep = disabler()
endif

linkexe = executable('linkedexe', 'linkexe.cc', dependencies : linkdep)
staticexe = executable('staticlinkedexe', 'linkexe.cc', dependencies : staticdep)
unitexe = executable('utf', 'unit_test.cpp', dependencies: testdep)
nomodexe = executable('nomod', 'nomod.cpp', dependencies : nomoddep)
extralibexe = executable('extralibexe', 'extralib.cpp', dependencies : extralibdep)

# python modules are shared libraries
python2module = shared_library('python2_module', ['python_module.cpp'], dependencies: [python2dep, bpython2dep], name_prefix: '', cpp_args: ['-DMOD_NAME=python2_module'])
python3module = shared_library('python3_module', ['python_module.cpp'], dependencies: [python3dep, bpython3dep], name_prefix: '', cpp_args: ['-DMOD_NAME=python3_module'])

test('Boost linktest', linkexe)
test('Boost statictest', staticexe)
test('Boost UTF test', unitexe)
test('Boost nomod', nomodexe)
test('Boost extralib test', extralibexe)

# explicitly use the correct python interpreter so that we don't have to provide two different python scripts that have different shebang lines
python2interpreter = find_program(python2.path(), required: false, disabler: true)
test('Boost Python2', python2interpreter, args: ['./test_python_module.py', meson.current_build_dir()], workdir: meson.current_source_dir(), depends: python2module)
python3interpreter = find_program(python3.path(), required: false, disabler: true)
test('Boost Python3', python3interpreter, args: ['./test_python_module.py', meson.current_build_dir()], workdir: meson.current_source_dir(), depends: python2module)

subdir('partial_dep')

# check we can apply a version constraint
dependency('boost', version: '>=@0@'.format(dep.version()))
