project('linker script', 'c')

cc = meson.get_compiler('c')

if build_machine.system() == 'cygwin'
  error('MESON_SKIP_TEST does not work on cygwin for some reason.')
endif

if cc.get_id() == 'clang-cl'
  error('MESON_SKIP_TEST uses lld which is not supported yet. Patches welcome.')
endif


# Static map file
if cc.get_id() == 'msvc'
  suffix = '.sym'
else
  suffix = '.map'
endif

mapfile = 'bob' + suffix

l = shared_library('bob', 'bob.c', symbol_export_file: mapfile)
e = executable('prog', 'prog.c', link_with : l)
test('core', e)

# configure_file
conf = configuration_data()
conf.set('in', 'bobMcBob')
m = configure_file(
  input : 'bob' + suffix + '.in',
  output : 'bob-conf' + suffix,
  configuration : conf,
)

l = shared_library('bob-conf', 'bob.c', symbol_export_file: m)
e = executable('prog-conf', 'prog.c', link_with : l)
test('core', e)

## custom_target
python = find_program('python3', required : false)
if not python.found()
  python = find_program('python')
endif
m = custom_target(
  'bob-ct' + suffix,
  command : [python, '@INPUT0@', '@INPUT1@', '@OUTPUT@'],
  input : ['copy.py', 'bob' + suffix],
  output : 'bob-ct' + suffix,
)

l = shared_library('bob-ct', ['bob.c', m], symbol_export_file: m)
e = executable('prog-ct', 'prog.c', link_with : l)
test('core', e)

# File
mapfile = files('bob' + suffix)

l = shared_library('bob-files', 'bob.c', symbol_export_file: mapfile)
e = executable('prog-files', 'prog.c', link_with : l)
test('core', e)

subdir('sub')

# With map file in subdir
mapfile = files('sub/foo' + suffix)

l = shared_library('bar', 'bob.c', symbol_export_file: mapfile)
e = executable('prog-bar', 'prog.c', link_with : l)
test('core', e)
