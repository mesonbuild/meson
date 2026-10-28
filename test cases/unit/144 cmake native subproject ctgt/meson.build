project('cmake native custom command')

if not add_languages('c', native: true, required: false)
  error('MESON_SKIP_TEST no C compiler for the build machine')
endif

# The generator is built for the build machine, so it must be run directly
# even when cross compiling with an exe_wrapper.
cm = import('cmake')
sub = cm.subproject('gen', native: true)
gen_dep = sub.dependency('genlib')

exe = executable('main', 'main.c', dependencies: gen_dep, native: true)
test('generated', exe)
