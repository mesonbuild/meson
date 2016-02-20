project('find program', 'c')

prog = find_program('program.py')

# Use either Python3 or 2 to run this
python = find_program('python3', required : false)
if not python.found()
  python = find_program('python')
endif

run_command(python, prog.path())
