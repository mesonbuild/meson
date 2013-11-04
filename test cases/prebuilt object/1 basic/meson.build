# This test is on its own because it is special.
# To run the test you need the prebuilt object
# file for the given platform.
#
# Combined with cross compilation this would make
# the state space explode so let's just keep this
# in its own subdir so it's not run during cross
# compilation tests.

project('prebuilt object', 'c')

object = 'linux-amd64.o'

# Remember: do not put source.c in this
# declaration. Only the prebuilt object. 
e = executable('prog', 'main.c',
objects : object)

test('objtest', e)
