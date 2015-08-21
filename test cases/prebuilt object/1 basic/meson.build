# This test is on its own because it is special.
# To run the test you need the prebuilt object
# file for the given platform.
#
# Combined with cross compilation this would make
# the state space explode so let's just keep this
# in its own subdir so it's not run during cross
# compilation tests.

project('prebuilt object', 'c')

if host_machine.system() == 'windows'
  prebuilt = 'prebuilt.obj'
else
  prebuilt = 'prebuilt.o'
endif

# Remember: do not put source.c in this
# declaration. run_tests.py generates the
# prebuilt object before running this test.

e = executable('prog', 'main.c',
objects : prebuilt)

test('objtest', e)
