# This test is on its own because it is special.
# To run the test you need the prebuilt object
# file for the given platform.
#
# Combined with cross compilation this would make
# the state space explode so let's just keep this
# in its own subdir so it's not run during cross
# compilation tests.

project('prebuilt object', 'c')

if host.name() == 'darwin'
  object = 'osx.o'
elif host.name() == 'linux'
  if meson.get_compiler('c').sizeof('void*') == 8
    object = 'linux-amd64.o'
  else
    object = 'linux-i386.o'
  endif
elif host.name() == 'windows'
  id = meson.get_compiler('c').get_id()
  if id == 'gcc'
    object = 'mingw.obj'
  elif id == 'msvc'
    object = 'msvc.obj'
  else
    error('Unknown compiler.')
  endif
else
  error('Unknown platform.')
endif

# Remember: do not put source.c in this
# declaration. Only the prebuilt object. 
e = executable('prog', 'main.c',
objects : object)

test('objtest', e)
