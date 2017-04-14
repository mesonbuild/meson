project('wintest', 'c')

# Test that we can produce an implib for an executable on Windows, and that it
# is installed along with the executable

prog = executable('prog', 'prog.c', install: true, implib: true)
test('wintest', prog)
