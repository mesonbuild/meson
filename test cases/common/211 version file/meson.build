project('linker script', 'c')

# Static map file
mapfile = 'bob.map'

l = shared_library('bob', 'bob.c', symbol_export_file: mapfile)
e = executable('prog', 'prog.c', link_with : l)
test('core', e)

# configure_file
conf = configuration_data()
conf.set('in', 'bobMcBob')
m = configure_file(
  input : 'bob.map.in',
  output : 'bob-conf.map',
  configuration : conf,
)

l = shared_library('bob-conf', 'bob.c', symbol_export_file: m)
e = executable('prog-conf', 'prog.c', link_with : l)
test('core', e)

# custom_target
python = find_program('python3')
m = custom_target(
  'bob-ct.map',
  command : [python, '@INPUT0@', '@INPUT1@', '@OUTPUT@'],
  input : ['copy.py', 'bob.map'],
  output : 'bob-ct.map',
)

l = shared_library('bob-ct', ['bob.c', m], symbol_export_file: m)
e = executable('prog-ct', 'prog.c', link_with : l)
test('core', e)

# File
mapfile = files('bob.map')

l = shared_library('bob-files', 'bob.c', symbol_export_file: mapfile)
e = executable('prog-files', 'prog.c', link_with : l)
test('core', e)

subdir('sub')

# With map file in subdir
mapfile = files('sub/foo.map')

l = shared_library('bar', 'bob.c', symbol_export_file: mapfile)
e = executable('prog-bar', 'prog.c', link_with : l)
test('core', e)
