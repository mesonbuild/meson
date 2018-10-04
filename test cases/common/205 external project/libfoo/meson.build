mod = import('unstable_external_project')

cc = meson.get_compiler('c')

# The configure script is a bash script that requires msys2
if cc.get_id() == 'msvc'
  error('MESON_SKIP_TEST: This test does not work with MSVC')
endif

if not find_program('make', required : false).found()
  error('MESON_SKIP_TEST: make not found')
endif

target_system = target_machine.system()
if target_system in ['windows', 'cygwin']
  libext = 'dll'
elif target_system == 'darwin'
  libext = 'dylib'
else
  libext = 'so'
endif

p = mod.add_project('configure',
  options : [
    '--prefix={prefix}',
    '--libdir=' + join_paths('{prefix}', '{libdir}'),
    '--includedir=' + join_paths('{prefix}', '{includedir}'),
    '--libext=' + libext,
  ],
  verbose : true,
)

libfoo_dep = p.dependency('foo')
