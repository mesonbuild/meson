project('find program', 'c')

prog = find_program('program.py')

# Python 3 is guaranteed to be available because Meson
# is implemented in it.
python = find_program('python3')

run_command(python, prog.path())
