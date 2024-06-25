project('jnijava', ['c', 'java'])

if build_machine.system() == 'cygwin'
  error('MESON_SKIP_TEST: cygwin test failures')
endif

if build_machine.system() == 'windows' and build_machine.cpu_family() == 'x86'
  error('MESON_SKIP_TEST: failing builds on 32bit Windows because a 32bit JDK is not available in the Azure Pipelines Windows images')
endif

fs = import('fs')
javamod = import('java')

cc = meson.get_compiler('c')
java = find_program('java')

jni_dep = dependency('jni', modules: ['jvm', 'awt'])
if jni_dep.version().version_compare('< 9')
  error('MESON_SKIP_TEST: this test requires Java 9')
endif

# Assert that the header can actually be found with the dependency.
cc.has_header('jni.h', dependencies: [jni_dep], required: true)
# Assert that the platform-specific include directory is included in the compiler arguments.
cc.has_header('jni_md.h', dependencies: [jni_dep], required: true)

subdir('src')

test(
  'jnitest',
  java,
  args: [
    '-jar',
    jnijar,
  ],
  protocol : 'exitcode',
)
