project('find program', 'c')

prog = find_program('program.py')

python = find_program('python3', required : false)
if not python.found()
  python = find_program('python')
endif

run_command(python, prog.path())

progf = files('program.py')
py = configure_file(input : 'program.py',
                    output : 'builtprogram.py',
                    configuration : configuration_data())

find_program(py)
find_program(progf)
