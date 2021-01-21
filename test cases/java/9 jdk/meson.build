project('jdkjava', ['c', 'java'])

if build_machine.system() == 'cygwin'
  error('MESON_SKIP_TEST: cygwin test failures')
endif

if build_machine.system() == 'windows' and build_machine.cpu_family() == 'x86'
  error('MESON_SKIP_TEST: failing builds on 32bit Windows because a 32bit JDK isn not available in the Azure Pipelines Windows images')
endif

fs = import('fs')

java = find_program('java')

jdk = dependency('jdk', version : '>=1.8')

subdir('lib')
subdir('src')
