project('find program', 'c')

prog = find_program('program.py')

python = find_program('python3', required : false)
if not python.found()
  python = find_program('python')
endif

run_command(python, prog.path())
