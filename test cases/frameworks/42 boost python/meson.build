# this test case can be deleted if support for unversioned python libs is removed

project('boost python test', 'cpp')

bm = build_machine.system()

if bm == 'windows' or bm == 'cygwin'
  error('MESON_SKIP_TEST: Windows uses different library files')
endif

dependency('boost', modules: ['python', 'numpy'], required: true)
dependency('boost', modules: ['python3', 'numpy3'], required: true)
dependency('boost', modules: ['python313', 'numpy313'], required: true)
dependency('boost', modules: ['python314', 'numpy314'], required: true)
dependency('boost', modules: ['python315', 'numpy315'], required: true)
