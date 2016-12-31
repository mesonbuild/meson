project('find program', 'c')

prog = find_program('program.py')

# Python 3 should always be available because Meson is implemented in it.
python = find_python3()

run_command(python, prog.path())
